import customtkinter as ctk


class CollapsibleSection(ctk.CTkFrame):
    def __init__(self, parent, title="Section", content=None, open_by_default=False, **kwargs):
        super().__init__(parent, **kwargs)

        self.open = open_by_default
        self.content_frame = None

        # Remove the header frame completely
        self.toggle_btn = ctk.CTkButton(
            self,
            text=f"▼ {title}" if open_by_default else f"▶ {title}",
            text_color="#fff",
            hover_color="#7573FC",
            border_width=0,
            anchor="w",
            command=self.toggle
        )
        self.toggle_btn.pack(fill="x", pady=(0, 0))

        # Content frame
        self.content_frame = ctk.CTkFrame(self)
        if open_by_default:
            self.content_frame.pack(fill="x", pady=(0,0))

        # Add custom content if provided
        if content:
            content(self.content_frame)

    def toggle(self):
        """Expand/collapse section content."""
        self.open = not self.open
        if self.open:
            self.toggle_btn.configure(text=self.toggle_btn.cget("text").replace("▶", "▼"))
            self.content_frame.pack(fill="x", pady=(0,0))
        else:
            self.toggle_btn.configure(text=self.toggle_btn.cget("text").replace("▼", "▶"))
            self.content_frame.pack_forget()


def create_sections(parent, sections: dict, start_open=None, layout="pack"):
    """
    Build multiple collapsible sections.

    Args:
        parent: The frame where the sections go.
        sections: dict -> {"SectionName": callback_to_build_content, ...}
        start_open: Section name to start open by default.
        layout: 'pack' or 'grid'.
    """
    section_objs = {}
    row = 0

    for title, content_func in sections.items():
        sec = CollapsibleSection(
            parent,
            title=title,
            content=content_func,
            open_by_default=(title == start_open),
        )

        section_objs[title] = sec

        if layout == "grid":
            sec.grid(row=row, column=0, sticky="ew", pady=4)
            parent.grid_rowconfigure(row, weight=0)
            parent.grid_columnconfigure(0, weight=1)
            row += 1
        else:
            sec.pack(fill="x", pady=4)

    return section_objs
