from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, List, Optional, Dict, Any
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import json
from datetime import datetime
from pathlib import Path
from PIL import ImageGrab, Image

# -----------------------------
# Data model
# -----------------------------

@dataclass
class Box:
    x1: float
    y1: float
    x2: float
    y2: float
    label: str = ""

    def normalized_xyxy(self) -> Tuple[float, float, float, float]:
        x1, y1, x2, y2 = self.x1, self.y1, self.x2, self.y2
        if x2 < x1: x1, x2 = x2, x1
        if y2 < y1: y1, y2 = y2, y1
        return x1, y1, x2, y2

    def move(self, dx: float, dy: float, W: int, H: int):
        x1, y1, x2, y2 = self.normalized_xyxy()
        w, h = x2 - x1, y2 - y1
        nx1, ny1 = max(0, min(W - w, x1 + dx)), max(0, min(H - h, y1 + dy))
        self.x1, self.y1, self.x2, self.y2 = nx1, ny1, nx1 + w, ny1 + h

    def resize_from_handle(self, handle: str, nx: float, ny: float, keep_inside: Tuple[int, int]):
        W, H = keep_inside
        x1, y1, x2, y2 = self.normalized_xyxy()
        if "n" in handle: y1 = max(0, min(ny, y2 - 1))
        if "s" in handle: y2 = min(H, max(ny, y1 + 1))
        if "w" in handle: x1 = max(0, min(nx, x2 - 1))
        if "e" in handle: x2 = min(W, max(nx, x1 + 1))
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2

# -----------------------------
# App
# -----------------------------

class AnnotatorApp(ctk.CTk):
    HANDLE_SIZE = 6
    HANDLE_NAMES = ("nw", "ne", "sw", "se", "n", "s", "w", "e")

    def __init__(self, start_image: Optional[Image.Image] = None, start_title: Optional[str] = None):
        super().__init__()

        self.title("Fast Annotator (crop + boxes)")
        self.geometry("1200x800")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # ---- State created BEFORE UI (so _build_ui can use it) ----
        self.mode = ctk.StringVar(value="Crop")   # used by segmented button
        self.selected_idx: Optional[int] = None   # selection in list/canvas

        # Image state
        self.img_path: Optional[Path] = None
        self.img_orig: Optional[Image.Image] = None
        self.photo: Optional[ImageTk.PhotoImage] = None
        self.W = 0
        self.H = 0

        # Build UI (needs self.mode)
        self._build_ui()

        # Persistent canvas items
        self.img_id = self.canvas.create_image(0, 0, anchor="nw")
        self.dim_ids = [
            self.canvas.create_rectangle(0,0,0,0, fill="#000000", stipple="gray50", width=0),
            self.canvas.create_rectangle(0,0,0,0, fill="#000000", stipple="gray50", width=0),
            self.canvas.create_rectangle(0,0,0,0, fill="#000000", stipple="gray50", width=0),
            self.canvas.create_rectangle(0,0,0,0, fill="#000000", stipple="gray50", width=0),
        ]
        # Crop visuals
        self.crop = Box(100, 100, 500, 350, "")
        self.crop_id = self.canvas.create_rectangle(0,0,0,0, outline="#00ffff", width=2, dash=(4,2))
        self.handle_ids = [self.canvas.create_rectangle(0,0,0,0, outline="#00ffff", fill="", width=2) for _ in range(8)]
        self.view = {"scale": 1.0, "ox": 0, "oy": 0}  # canvas ← image transform

        # Boxes (annotations)
        self.boxes: List[Box] = []
        self.box_item_ids: List[Tuple[int, int]] = []  # (rect_id, text_id)

        # Temp draw rectangle (while dragging new box)
        self.temp_id = self.canvas.create_rectangle(0,0,0,0, outline="#ffffff", dash=(2,2), width=1)
        self.canvas.itemconfigure(self.temp_id, state="hidden")
        self.temp_box: Optional[Box] = None

        # Drag state
        self.dragging = False
        self.drag_target = None   # interaction tuple
        self.drag_last = (0, 0)

        # Redraw throttle
        self._redraw_pending = False

        # Events
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # If a start image was provided, load it immediately
        if start_image is not None:
            self.img_orig = start_image.convert("RGB")
            self.W, self.H = self.img_orig.width, self.img_orig.height
            self._set_photo(self.img_orig)
            margin = max(10, int(min(self.W, self.H) * 0.05))
            self.crop = Box(margin, margin, min(self.W - margin, margin + 400), min(self.H - margin, margin + 250))
            self._request_redraw()
        else:
            self._request_redraw()

    # ------------- UI --------------

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=30)
        self.grid_columnconfigure(1, weight=2)

        # Canvas on the left
        self.canvas = ctk.CTkCanvas(self, bg="#1a1a1a", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Sidebar on the right
        sidebar = ctk.CTkFrame(self)
        sidebar.grid(row=0, column=1, sticky="nsew")
        sidebar.grid_propagate(False)

        # Segmented toggle for tool
        tool_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        tool_row.pack(padx=(10,10), pady=(10, 0), fill="x")
        ctk.CTkLabel(tool_row, text="Tool:", font=("Segoe UI", 13, "bold")).pack(side="left", padx=(0, 10))
        self.tool_segment = ctk.CTkSegmentedButton(tool_row, values=["Crop", "Label"], variable=self.mode, command=self._on_tool_change)
        self.tool_segment.pack(side="left", fill="x", expand=True)
        self.tool_segment.set("Crop")

        # Boxes list header
        list_hdr = ctk.CTkLabel(sidebar, text="Label List", anchor="w",font=("Segoe UI", 13, "bold"))
        list_hdr.pack(padx=(10,10), pady=(10,0), fill="x")

        # Scrollable list container
        self.box_list = ctk.CTkScrollableFrame(sidebar, height=320)
        self.box_list.pack(padx=(10,10), pady=(0, 10), fill="both", expand=True)

        save_btn = ctk.CTkButton(sidebar, text="Save Crop + Labels", command=self._save_crop_and_labels)
        save_btn.pack(padx=(10,10), pady=(10, 10), fill="x")

        help_txt = ctk.CTkLabel(sidebar, justify="left", text=(
            "Controls:\n"
            " • Crop: drag inside to move; handles resize.\n"
            " • Box: click-drag to draw; drag box/handles to move/resize.\n"
            " • Edit labels or delete from the list.\n"
            " • Save exports PNG + JSON."
        ))
        help_txt.pack(padx=12, pady=12, fill="x")

    def _on_tool_change(self, *_):
        self._request_redraw()

    # ------------- Image I/O -------------

    def _set_photo(self, img: Image.Image):
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            # Defer until canvas is realized
            self.after(50, lambda: self._set_photo(img))
            return

        img_w, img_h = img.size
        scale = min(canvas_w / img_w, canvas_h / img_h, 1.0)  # do not upscale
        view_w = int(img_w * scale)
        view_h = int(img_h * scale)

        # Centered offset
        ox = (canvas_w - view_w) // 2
        oy = (canvas_h - view_h) // 2

        # Save view transform for all conversions
        self.view.update({"scale": scale, "ox": ox, "oy": oy})

        # Draw the image
        resized = img.resize((view_w, view_h), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized, master=self.canvas)
        self.canvas.itemconfigure(self.img_id, image=self.photo)
        self.canvas.coords(self.img_id, ox, oy)

        # Bookkeeping (original image size still lives in image space)
        self.W, self.H = img_w, img_h
        self.canvas.config(scrollregion=(0, 0, canvas_w, canvas_h))

        # Request redraw of overlays in the new view
        self._request_redraw()



    # ------------- Redraw (fast + throttled) -------------

    def _request_redraw(self):
        if not self._redraw_pending:
            self._redraw_pending = True
            self.after_idle(self._do_redraw)

    def _do_redraw(self):
        self._redraw_pending = False
        self._redraw_fast()

    def _layout_handles(self, box: Box):
        """
        Lay out resize handles in **canvas space** by projecting the box's
        image-space points via img_to_canvas().
        """
        x1, y1, x2, y2 = box.normalized_xyxy()
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        pts_img = [
            (x1, y1), (x2, y1), (x1, y2), (x2, y2),
            (cx, y1), (cx, y2), (x1, cy), (x2, cy)
        ]
        s = self.HANDLE_SIZE
        for hid, (ix, iy) in zip(self.handle_ids, pts_img):
            cxp, cyp = self.img_to_canvas(ix, iy)
            self.canvas.coords(hid, cxp - s, cyp - s, cxp + s, cyp + s)
            self.canvas.itemconfigure(hid, state="normal")


    def _layout_dim(self, focus: Box):
        """
        Draw 4 dim rectangles around the crop, aligned to the displayed image
        (i.e., **canvas space**). We build the four strips using the image
        rectangle in canvas coords, minus the crop rect in canvas coords.
        """
        if not self.img_orig:
            for rid in self.dim_ids:
                self.canvas.itemconfigure(rid, state="hidden")
            return

        # Image bounds in canvas coords
        s = self.view.get("scale", 1.0)
        ox, oy = self.view.get("ox", 0), self.view.get("oy", 0)
        img_cx1, img_cy1 = ox, oy
        img_cx2, img_cy2 = ox + self.W * s, oy + self.H * s

        # Crop in canvas coords
        x1, y1, x2, y2 = focus.normalized_xyxy()
        cx1, cy1 = self.img_to_canvas(x1, y1)
        cx2, cy2 = self.img_to_canvas(x2, y2)

        coords = [
            (img_cx1, img_cy1, img_cx2, max(img_cy1, cy1)),   # top
            (max(cx2, img_cx1), max(cy1, img_cy1), img_cx2, min(cy2, img_cy2)),  # right
            (img_cx1, min(cy2, img_cy2), img_cx2, img_cy2),   # bottom
            (img_cx1, max(cy1, img_cy1), max(cx1, img_cx1), min(cy2, img_cy2)),  # left
        ]
        for rid, c in zip(self.dim_ids, coords):
            self.canvas.coords(rid, *c)
            self.canvas.itemconfigure(rid, state="normal")


    def _ensure_box_items(self):
        need = len(self.boxes) - len(self.box_item_ids)
        for _ in range(need):
            r = self.canvas.create_rectangle(0, 0, 0, 0, width=2)
            t = self.canvas.create_text(0, 0, anchor="sw", font=("Segoe UI", 11, "bold"))
            self.box_item_ids.append((r, t))

    def _redraw_fast(self):
        """
        Draw everything in **canvas space** (project from image space).
        """
        if self.img_orig:
            # Crop
            self.canvas.itemconfigure(self.crop_id, state="normal")
            x1, y1, x2, y2 = self.crop.normalized_xyxy()
            cx1, cy1 = self.img_to_canvas(x1, y1)
            cx2, cy2 = self.img_to_canvas(x2, y2)
            self.canvas.coords(self.crop_id, cx1, cy1, cx2, cy2)
            self._layout_handles(self.crop)
            self._layout_dim(self.crop)
        else:
            self.canvas.itemconfigure(self.crop_id, state="hidden")
            for hid in self.handle_ids:
                self.canvas.itemconfigure(hid, state="hidden")
            for rid in self.dim_ids:
                self.canvas.itemconfigure(rid, state="hidden")

        # Annotation boxes
        self._ensure_box_items()
        for i, (rid, tid) in enumerate(self.box_item_ids):
            if i < len(self.boxes):
                b = self.boxes[i]
                bx1, by1, bx2, by2 = b.normalized_xyxy()
                cx1, cy1 = self.img_to_canvas(bx1, by1)
                cx2, cy2 = self.img_to_canvas(bx2, by2)
                self.canvas.coords(rid, cx1, cy1, cx2, cy2)
                is_sel = (self.selected_idx == i)
                color = "#ffd400" if is_sel else "#ff6a00"
                self.canvas.itemconfigure(rid, outline=color)
                self.canvas.coords(tid, cx1 + 4, max(0, cy1 - 6))
                self.canvas.itemconfigure(tid, text=b.label or f"box_{i+1}", fill=color, state="normal")
                self.canvas.itemconfigure(rid, state="normal")
            else:
                self.canvas.itemconfigure(rid, state="hidden")
                self.canvas.itemconfigure(tid, state="hidden")

        # Temp drawing
        if self.temp_box is not None and self.mode.get() == "Label":
            x1, y1, x2, y2 = self.temp_box.normalized_xyxy()
            cx1, cy1 = self.img_to_canvas(x1, y1)
            cx2, cy2 = self.img_to_canvas(x2, y2)
            self.canvas.coords(self.temp_id, cx1, cy1, cx2, cy2)
            self.canvas.itemconfigure(self.temp_id, state="normal")
        else:
            self.canvas.itemconfigure(self.temp_id, state="hidden")


    # ------------- Hit-testing -------------

    def _hit_handle(self, box: Box, x: float, y: float) -> Optional[str]:
        """
        Hit-test in **image space**. Because the mouse lives in canvas space
        but we convert it to image space before calling this, we must scale
        the handle radius back into image units so hit areas feel consistent
        regardless of zoom.
        """
        x1, y1, x2, y2 = box.normalized_xyxy()
        # Convert HANDLE_SIZE (canvas px) to image-space units
        s = self.HANDLE_SIZE + 2
        scale = max(1e-6, self.view.get("scale", 1.0))
        r = s / scale  # handle half-size in image units

        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        regions = {
            "nw": (x1 - r, y1 - r, x1 + r, y1 + r),
            "ne": (x2 - r, y1 - r, x2 + r, y1 + r),
            "sw": (x1 - r, y2 - r, x1 + r, y2 + r),
            "se": (x2 - r, y2 - r, x2 + r, y2 + r),
            "n": (cx - r, y1 - r, cx + r, y1 + r),
            "s": (cx - r, y2 - r, cx + r, y2 + r),
            "w": (x1 - r, cy - r, x1 + r, cy + r),
            "e": (x2 - r, cy - r, x2 + r, cy + r),
        }
        for name, (ax1, ay1, ax2, ay2) in regions.items():
            if ax1 <= x <= ax2 and ay1 <= y <= ay2:
                return name
        return None

    def _hit_inside(self, box: Box, x: float, y: float) -> bool:
        x1, y1, x2, y2 = box.normalized_xyxy()
        return x1 <= x <= x2 and y1 <= y <= y2

    def _hit_box(self, x: float, y: float) -> Optional[int]:
        for i in reversed(range(len(self.boxes))):
            if self._hit_inside(self.boxes[i], x, y) or self._hit_handle(self.boxes[i], x, y):
                return i
        return None

    # ------------- Mouse events -------------

    def _on_canvas_resize(self, event):
        if self.img_orig:
            self._set_photo(self.img_orig)
        self._request_redraw()

    def _on_motion(self, evt):
        """
        Cursor feedback based on **image-space** hit-tests.
        """
        x_canvas, y_canvas = evt.x, evt.y
        ix, iy = self.canvas_to_img(x_canvas, y_canvas)
        cur = "arrow"
        m = self.mode.get()
        if m == "Crop":
            h = self._hit_handle(self.crop, ix, iy)
            if h:
                cur = self._cursor_for_handle(h)
            elif self._hit_inside(self.crop, ix, iy):
                cur = "fleur"
        elif m == "Label":
            idx = self._hit_box(ix, iy)  # image-space
            if idx is not None:
                h = self._hit_handle(self.boxes[idx], ix, iy)
                if h:
                    cur = self._cursor_for_handle(h)
                else:
                    cur = "fleur"
            else:
                cur = "tcross"
        self.canvas.configure(cursor=cur)

    def _cursor_for_handle(self, h: str) -> str:
        return {
            "nw": "top_left_corner",
            "ne": "top_right_corner",
            "sw": "bottom_left_corner",
            "se": "bottom_right_corner",
            "n": "top_side",
            "s": "bottom_side",
            "w": "left_side",
            "e": "right_side",
        }.get(h, "arrow")

    def _on_press(self, evt):
        if not self.img_orig:
            return
        # Convert mouse to **image space**
        ix, iy = self.canvas_to_img(evt.x, evt.y)
        ix, iy = self._clamp(ix, iy)  # clamp in image units
        self.dragging = True
        self.drag_last = (ix, iy)
        m = self.mode.get()

        if m == "Crop":
            h = self._hit_handle(self.crop, ix, iy)
            if h:
                self.drag_target = ("crop-handle", h)
            elif self._hit_inside(self.crop, ix, iy):
                self.drag_target = ("crop-move",)
            else:
                self.drag_target = ("crop-move",)
        else:  # box mode
            idx = self._hit_box(ix, iy)
            if idx is not None:
                h = self._hit_handle(self.boxes[idx], ix, iy)
                if h:
                    self.drag_target = ("box-handle", idx, h)
                elif self._hit_inside(self.boxes[idx], ix, iy):
                    self.drag_target = ("box-move", idx)
                    self.selected_idx = idx
                    self._request_redraw()
            else:
                self.temp_box = Box(ix, iy, ix, iy, "")
                self.drag_target = ("new-box",)

        self._request_redraw()


    def _on_drag(self, evt):
        if not self.dragging or not self.img_orig:
            return
        # Convert to **image space**
        ix, iy = self.canvas_to_img(evt.x, evt.y)
        ix, iy = self._clamp(ix, iy)
        lx, ly = self.drag_last
        dx, dy = ix - lx, iy - ly
        self.drag_last = (ix, iy)

        if not self.drag_target:
            return

        kind = self.drag_target[0]

        if kind == "crop-move":
            self.crop.move(dx, dy, self.W, self.H)

        elif kind == "crop-handle":
            handle = self.drag_target[1]
            self.crop.resize_from_handle(handle, ix, iy, (self.W, self.H))

        elif kind == "box-move":
            idx = self.drag_target[1]
            self.boxes[idx].move(dx, dy, self.W, self.H)

        elif kind == "box-handle":
            idx, handle = self.drag_target[1], self.drag_target[2]
            self.boxes[idx].resize_from_handle(handle, ix, iy, (self.W, self.H))

        elif kind == "new-box":
            if self.temp_box is not None:
                self.temp_box.x2, self.temp_box.y2 = ix, iy

        self._request_redraw()


    def _on_release(self, _evt):
        if not self.dragging:
            return
        self.dragging = False

        if self.drag_target and self.drag_target[0] == "new-box" and self.temp_box is not None:
            x1, y1, x2, y2 = self.temp_box.normalized_xyxy()
            if abs(x2 - x1) > 3 and abs(y2 - y1) > 3:
                self.boxes.append(self.temp_box)
                self.selected_idx = len(self.boxes) - 1
                self._refresh_box_list()
            self.temp_box = None

        self.drag_target = None
        self._request_redraw()

    # ------------- Save crop + labels -------------

    def _save_crop_and_labels(self):
        if not self.img_orig:
            messagebox.showwarning("No image", "Open an image first.")
            return

        cx1, cy1, cx2, cy2 = [int(round(v)) for v in self.crop.normalized_xyxy()]
        cx1 = max(0, min(self.W, cx1))
        cy1 = max(0, min(self.H, cy1))
        cx2 = max(0, min(self.W, cx2))
        cy2 = max(0, min(self.H, cy2))
        if cx2 <= cx1 or cy2 <= cy1:
            messagebox.showwarning("Invalid crop", "Crop area is empty.")
            return

        default_name = "Crop" if not self.img_path else self.img_path.stem + "_crop"
        save_path = filedialog.asksaveasfilename(
            title="Save cropped image",
            initialfile=f"{default_name}.png",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")]
        )
        if not save_path:
            return
        base = Path(save_path)
        img_out_path = base.with_suffix(".png")
        labels_out_path = base.with_name(base.stem + "_labels.json")

        cropped = self.img_orig.crop((cx1, cy1, cx2, cy2))
        try:
            cropped.save(img_out_path)
        except Exception as e:
            messagebox.showerror("Save failed", f"Could not save image:\n{e}")
            return

        newW, newH = cropped.width, cropped.height

        out_labels: List[Dict[str, Any]] = []
        for b in self.boxes:
            bx1, by1, bx2, by2 = b.normalized_xyxy()
            ix1 = max(cx1, bx1)
            iy1 = max(cy1, by1)
            ix2 = min(cx2, bx2)
            iy2 = min(cy2, by2)
            if ix2 <= ix1 or iy2 <= iy1:
                continue

            rx1 = ix1 - cx1
            ry1 = iy1 - cy1
            rx2 = ix2 - cx1
            ry2 = iy2 - cy1

            nx1 = rx1 / newW
            ny1 = ry1 / newH
            nx2 = rx2 / newW
            ny2 = ry2 / newH

            out_labels.append({
                "label": b.label,
                "box_pixels": [int(round(rx1)), int(round(ry1)), int(round(rx2)), int(round(ry2))],
                "box_normalized": [float(nx1), float(ny1), float(nx2), float(ny2)]
            })

        payload = {
            "image": {"path": str(img_out_path), "width": newW, "height": newH},
            "labels": out_labels,
            "meta": {
                "source_image": str(self.img_path) if self.img_path else None,
                "crop_from": [cx1, cy1, cx2, cy2],
                "format": "xyxy",
                "normalized_range": [0.0, 1.0],
            }
        }

        try:
            with open(labels_out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            messagebox.showerror("Save failed", f"Could not save labels JSON:\n{e}")
            return

        messagebox.showinfo("Saved", f"Image: {img_out_path.name}\nLabels: {labels_out_path.name}")

    # ------------- Helpers -------------

    def _clamp(self, x: float, y: float) -> Tuple[int, int]:
        x = max(0, min(self.W, x))
        y = max(0, min(self.H, y))
        return int(x), int(y)

    def _refresh_box_list(self):
        for child in self.box_list.winfo_children():
            child.destroy()
        for i, b in enumerate(self.boxes):
            self._make_box_row(i, b)

    def _make_box_row(self, idx, box):
        # Parent uses pack; this inner frame can use grid safely
        row = ctk.CTkFrame(self.box_list)
        row.pack(fill="x", padx=8, pady=4)

        # Make the entry column expand
        row.grid_columnconfigure(0, weight=0)   # index
        row.grid_columnconfigure(1, weight=1)   # entry (stretch)
        row.grid_columnconfigure(2, weight=0)   # select
        row.grid_columnconfigure(3, weight=0)   # delete

        # Index badge
        idx_lbl = ctk.CTkLabel(row, text=f"#{idx+1}", width=36, anchor="center")
        idx_lbl.grid(row=0, column=0, padx=(0,0), pady=(10,10), sticky="w")

        # Editable label (stretches with row width)
        entry = ctk.CTkEntry(row)
        entry.insert(0, box.label or f"box_{idx+1}")
        entry.grid(row=0, column=1, padx=(0, 10), pady=(10,10), sticky="ew")

        def commit_label(_evt=None, i=idx, e=entry):
            self._update_box_label(i, e.get())
        entry.bind("<Return>", commit_label)
        entry.bind("<FocusOut>", commit_label)

        # Keep uniform button widths for a clean look
        sel_btn = ctk.CTkButton(row, text="Select", width=80, command=lambda i=idx: self._select_box(i))
        sel_btn.grid(row=0, column=2, padx=(0, 10),  pady=(10,10), sticky="e")

        del_btn = ctk.CTkButton(row, text="❌", width=20, fg_color="#aa2e2e", hover_color="#8e2424", command=lambda i=idx: self._delete_box_at(i))
        del_btn.grid(row=0, column=3, padx=(0, 10),  pady=(10,10), sticky="e")

    def _update_box_label(self, idx: int, new_label: str):
        if 0 <= idx < len(self.boxes):
            self.boxes[idx].label = new_label.strip()
            self._request_redraw()

    def _select_box(self, idx: int):
        if 0 <= idx < len(self.boxes):
            self.selected_idx = idx
            self._request_redraw()
            try:
                row = self.box_list.winfo_children()[idx]
                row.focus_set()
            except Exception:
                pass

    def _delete_box_at(self, idx: int):
        if 0 <= idx < len(self.boxes):
            self.boxes.pop(idx)
            if self.selected_idx == idx:
                self.selected_idx = None
            elif self.selected_idx is not None and self.selected_idx > idx:
                self.selected_idx -= 1
            self._refresh_box_list()
            self._request_redraw()
            
    def img_to_canvas(self, x: float, y: float) -> tuple[float, float]:
        s, ox, oy = self.view["scale"], self.view["ox"], self.view["oy"]
        return ox + x * s, oy + y * s

    def canvas_to_img(self, x: float, y: float) -> tuple[float, float]:
        s, ox, oy = self.view["scale"], self.view["ox"], self.view["oy"]
        return (x - ox) / s, (y - oy) / s



def _grab_widget_image(widget) -> Image.Image:
    # ensure geometry is current
    try:
        widget.update_idletasks()
    except Exception:
        pass
    x1 = widget.winfo_rootx()
    y1 = widget.winfo_rooty()
    x2 = x1 + widget.winfo_width()
    y2 = y1 + widget.winfo_height()
    return ImageGrab.grab(bbox=(x1, y1, x2, y2))

def advanced_screenshot_from_widget(widget):
    """
    Capture the given Tk/CTk widget and open AnnotatorApp with the image preloaded.
    Call this from your gui.py button handler, e.g.:
        from temp import advanced_screenshot_from_widget
        ...
        advanced_screenshot_from_widget(web_frame)
    """
    try:
        img = _grab_widget_image(widget)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pseudo_name = f"screenshot_{timestamp}.png"
        app = AnnotatorApp(start_image=img, start_title=f"Annotator – {pseudo_name}")
        app.mainloop()
        return True, f"Annotator closed for {pseudo_name}"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Annotation error: {e!r}"
