from pathlib import Path

file_path = Path(r"c:\Users\ADMIN\Desktop\Capstone\Application\source\FinstockEventScope\app\ui\widgets.py")
content = file_path.read_text(encoding="utf-8")

old_start = "        for index in range(rows * 7):"
old_end = "            self.setCellWidget(index // 7, index % 7, cell)"

new_loop = """        for index in range(rows * 7):
            day = first + timedelta(days=index)
            day_events = sorted(by_day.get(day.isoformat(), []), key=lambda pair: pair[0].get(pair[1]) or "")
            
            cell = QFrame()
            cell.setObjectName("dayCell")
            cell.setCursor(Qt.PointingHandCursor)
            layout = QVBoxLayout(cell)
            layout.setContentsMargins(6, 4, 6, 4)
            layout.setSpacing(2)
            
            # --- Header Row: Date & Event Count Pill ---
            header_row = QHBoxLayout()
            header_row.setContentsMargins(0, 0, 0, 0)
            header_row.setSpacing(4)
            
            day_text = day.strftime("%d %b") if day.day == 1 else day.strftime("%d")
            day_num_lbl = QLabel(day_text)
            
            is_in_active_month = (anchor_month is None) or (day.month == anchor_month)
            
            if day == today:
                day_num_lbl.setStyleSheet("background: #2563EB; color: #FFFFFF; font-weight: 800; font-size: 11px; border-radius: 9px; padding: 1px 6px;")
            elif is_in_active_month:
                day_num_lbl.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 12px;" if is_dark else "color: #0A192F; font-weight: 700; font-size: 12px;")
            else:
                day_num_lbl.setStyleSheet("color: #475569; font-weight: 500; font-size: 11px;" if is_dark else "color: #94A3B8; font-weight: 500; font-size: 11px;")
                    
            header_row.addWidget(day_num_lbl)
            header_row.addStretch()
            
            if day_events:
                cnt_lbl = QLabel(f"● {len(day_events):,}")
                cnt_lbl.setStyleSheet(
                    "color: #38BDF8; font-size: 10px; font-weight: 700; background: #0E223D; border-radius: 5px; padding: 1px 5px;"
                    if is_dark else
                    "color: #1D4ED8; font-size: 10px; font-weight: 700; background: #DBEAFE; border-radius: 5px; padding: 1px 5px;"
                )
                header_row.addWidget(cnt_lbl)
                
            layout.addLayout(header_row)

            # --- Sleek Single-Line Event Chips (No Text Wrap, Clean 2026 Layout) ---
            for event, field in day_events[:2]:
                pill = QPushButton()
                pill.setCursor(Qt.PointingHandCursor)
                kind = event.get("kind", "Economic")
                dot_color = {"Economic": "#38BDF8", "Corporate": "#34D399", "Regulatory": "#FBBF24"}.get(kind, "#60A5FA")
                
                title = event.get("title", "")
                if len(title) > 22:
                    title = title[:20] + "…"
                pill.setText(f" {title}")
                pill.setToolTip(f"{event.get('title')}\\nType: {kind}\\nAuthority: {event.get('authority', 'N/A')}\\nTime: {display_time(event.get(field), zone)}")
                
                pill_bg = "#0B1A2F" if is_dark else "#F1F5F9"
                pill_border = "#162D4A" if is_dark else "#CBD5E1"
                pill_text = "#E2E8F0" if is_dark else "#0A192F"
                pill.setStyleSheet(f\"\"\"
                    QPushButton {{
                        background: {pill_bg};
                        border: 1px solid {pill_border};
                        border-left: 3px solid {dot_color};
                        border-radius: 3px;
                        color: {pill_text};
                        font-size: 10px;
                        font-weight: 600;
                        text-align: left;
                        padding: 1px 4px;
                        max-height: 18px;
                    }}
                    QPushButton:hover {{
                        background: #1E3A8A;
                        border-color: #3B82F6;
                        color: #FFFFFF;
                    }}
                \"\"\")
                ev_id = event["id"]
                pill.clicked.connect(lambda checked=False, eid=ev_id: self.event_selected.emit(eid))
                layout.addWidget(pill)

            if len(day_events) > 2:
                more_btn = QPushButton(f"+{len(day_events) - 2} more…")
                more_btn.setCursor(Qt.PointingHandCursor)
                more_btn.setStyleSheet(f\"\"\"
                    QPushButton {{
                        background: transparent;
                        border: 0;
                        color: {"#38BDF8" if is_dark else "#2563EB"};
                        font-size: 10px;
                        font-weight: 700;
                        text-align: left;
                        padding: 0 4px;
                        max-height: 16px;
                    }}
                    QPushButton:hover {{
                        color: #60A5FA;
                        text-decoration: underline;
                    }}
                \"\"\")
                cur_day = day
                more_btn.clicked.connect(lambda checked=False, d=cur_day: self.day_selected.emit(d))
                layout.addWidget(more_btn)

            layout.addStretch()

            def make_cell_click(d):
                return lambda ev: self.day_selected.emit(d)

            cell.mousePressEvent = make_cell_click(day)
            self.setCellWidget(index // 7, index % 7, cell)"""

idx1 = content.find(old_start)
idx2 = content.find(old_end, idx1)
if idx1 != -1 and idx2 != -1:
    idx2 += len(old_end)
    content = content[:idx1] + new_loop + content[idx2:]
    file_path.write_text(content, encoding="utf-8")
    print("CalendarGrid successfully patched!")
else:
    print(f"Indices: {idx1}, {idx2}")
