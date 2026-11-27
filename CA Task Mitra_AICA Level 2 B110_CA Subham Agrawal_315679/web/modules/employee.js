WD.mod("employee", {
  nav: [{ id: "my", l: "My work", sub: "my_dashboard" }, { id: "load", l: "Team workload", sub: "workload", roles: ["ca", "manager"] }, { id: "att", l: "Attendance", sub: "attendance" }, { id: "ts", l: "Timesheet", sub: "timesheet" }],
  views: {
    async my(el) {
      const d = await api("employee/my");
      el.replaceChildren(h("h2", {}, "My work"), h("div", { class: "grid" }, stat("Open tasks", d.open.length), stat("Overdue", d.overdue), stat("Completed", d.done), stat("Hours this month", d.hours_month)),
        table([{ l: "Due", f: r => [r.due_date || "—", r.overdue ? h("span", { class: "badge b-od" }, "Overdue") : ""] }, { l: "Task", k: "title" }, { l: "Client", k: "client" }, { l: "Status", f: r => badge(r.status) }], d.open, r => WD.openAssignment(r.id, () => go("employee", "my"))));
    },
    async load(el) {
      const rows = await api("employee/workload");
      el.replaceChildren(h("h2", {}, "Team workload"), table([{ k: "name", l: "Employee" }, { k: "designation", l: "Designation" }, { k: "open_tasks", l: "Open tasks" }, { k: "overdue", l: "Overdue" }, { k: "in_review", l: "In review" }, { k: "hours_month", l: "Hours (month)" }], rows));
    },
    async att(el) {
      const draw = async () => { const rows = await api("employee/attendance");
        el.replaceChildren(h("div", { class: "row" }, h("h2", { style: "margin:0" }, "Attendance"), h("span", { class: "sp" }), h("button", { class: "btn ok", onclick: () => act(async () => { await post("employee/attendance/in"); draw(); }, "Checked in") }, "Check in"), h("button", { class: "btn sec", onclick: () => act(async () => { await post("employee/attendance/out"); draw(); }, "Checked out") }, "Check out")),
          table([{ k: "name", l: "Employee" }, { k: "day", l: "Date" }, { k: "in_time", l: "In" }, { k: "out_time", l: "Out" }], rows)); }; await draw();
    },
    async ts(el) {
      const draw = async () => { const rows = await api("employee/timesheet"), mine = await api("employee/my");
        el.replaceChildren(h("div", { class: "row" }, h("h2", { style: "margin:0" }, "Timesheet"), h("span", { class: "sp" }),
          h("button", { class: "btn", onclick: () => formModal("Log hours", [{ k: "assignment_id", l: "Assignment", t: "select", o: opt(mine.open, "id", "title") }, { k: "hours", l: "Hours", t: "number", req: 1 }, { k: "day", l: "Date", t: "date" }, { k: "note", l: "Note" }], {}, async d => { await post("employee/timesheet", d); draw(); }) }, "+ Log hours")),
          table([{ k: "day", l: "Date" }, { k: "employee", l: "Employee" }, { k: "title", l: "Assignment" }, { k: "hours", l: "Hours" }, { k: "note", l: "Note" }], rows)); }; await draw();
    }
  }
});

WD.hooks.dashboard.push(async (grid) => {
  if (!isBoss() || !on("employee", "attendance")) return;
  const rows = await api("employee/today"); const here = rows.filter(r => r.in_time).length;
  grid.append(dbox("🧑‍💼 Employees today", [h("div", { class: "kpis" }, kpi("Reached", here, "grn"), kpi("Yet to come", rows.length - here, rows.length - here ? "amb" : ""), kpi("Total", rows.length)),
    table([{ k: "name", l: "Employee" }, { l: "In", f: r => r.in_time || "—" }, { l: "Out", f: r => r.out_time || "—" }, { l: "Status", f: r => badge(r.state) }], rows)], { order: 3 }));
});
