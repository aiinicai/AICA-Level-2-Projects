(async function (supplied) {
  if (location.hostname !== "udin.icai.org" || location.protocol !== "https:" ||
      !/^\/ICAI\/generateUDIN\/?$/i.test(location.pathname)) {
    alert("Open the official ICAI Generate UDIN page after signing in.");
    return;
  }
  const pasted = supplied || prompt("Paste the autofill data copied from Net Worth Office.");
  if (!pasted) return;
  let data;
  try {
    data = supplied || JSON.parse(pasted);
    if (data.format !== "net-worth-office-udin-v1" || data.figures?.length !== 2) throw Error();
  } catch {
    alert("Use Copy autofill data in Net Worth Office, then paste it here.");
    return;
  }
  const done = [], pending = [];
  const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
  async function until(check, attempts = 24) {
    for (let attempt = 0; attempt < attempts; attempt++) {
      const result = check();
      if (result) return result;
      await pause(250);
    }
    return false;
  }
  const norm = value => String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  const visible = node => node && node.getClientRects().length && !node.disabled && !node.readOnly;
  const text = node => norm(node.innerText || node.textContent);
  const labels = () => [...document.querySelectorAll("label,legend,mat-label,.form-label,[role=radio],.col-form-label")];
  const find = (regex, selector) => {
    const inputs = [...document.querySelectorAll(selector)].filter(visible);
    const ranked = inputs.find(node => regex.test(norm([
      node.getAttribute("aria-label"), node.getAttribute("formcontrolname"), node.placeholder, node.name, node.id,
      ...[...(node.labels || [])].map(text)
    ].join(" "))));
    if (ranked) return ranked;
    for (const label of labels().filter(node => regex.test(text(node)))) {
      if (visible(label.control) && label.control.matches(selector)) return label.control;
      let parent = label.parentElement;
      for (let i = 0; parent && i < 2; i++, parent = parent.parentElement) {
        const matches = [...parent.querySelectorAll(selector)].filter(visible);
        if (matches.length === 1) return matches[0];
      }
    }
  };
  const inputSelector = "input:not([type=hidden]):not([type=radio]):not([type=checkbox]),textarea";
  function set(node, value) {
    if (!visible(node)) return false;
    const native = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(node), "value")?.set;
    if (native) native.call(node, value); else node.value = value;
    node.dispatchEvent(new Event("input", { bubbles: true }));
    node.dispatchEvent(new Event("change", { bubbles: true }));
    node.dispatchEvent(new Event("blur", { bubbles: true }));
    return node.value === value;
  }
  async function choice(regex, wanted, exactControl, keepOpen = false) {
    const control = exactControl || find(regex, "select,[role=combobox],ng-select,mat-select,.select2-selection");
    if (!control || !wanted) return false;
    const match = label => norm(label) === norm(wanted) || norm(label).startsWith(norm(wanted) + " ");
    if (control.matches("select")) {
      const option = [...control.options].find(opt => match(opt.textContent));
      return !!option && (control.value === option.value || set(control, option.value));
    }
    const selectedText = () => control.querySelector(".ng-value-label,.mat-select-value-text")?.textContent ||
      control.innerText;
    if (match(selectedText())) return true;
    const trigger = control.querySelector(".ng-select-container,[role=combobox]") || control;
    trigger.scrollIntoView({block:"center"});
    if (!control.classList.contains("ng-select-opened")) {
      trigger.dispatchEvent(new MouseEvent("mousedown", {bubbles:true,cancelable:true,button:0}));
      // ng-select opens on mousedown. Other dropdowns use click.
      if (!control.classList.contains("ng-select-opened")) trigger.click();
    }
    const options = () => {
      const owner = control.querySelector("[aria-controls]") || control;
      const list = document.getElementById(owner.getAttribute("aria-controls"));
      return [...(list || document).querySelectorAll("[role=option],.ng-option,.select2-results__option,mat-option")]
        .filter(node => visible(node) && node.getAttribute("aria-disabled") !== "true");
    };
    const option = await until(() => options().find(node => match(node.innerText)));
    if (option) {
      option.click();
      return !!await until(() => match(selectedText()));
    }
    if (!keepOpen) {
      const focused = control.querySelector("input") || document.activeElement;
      focused?.dispatchEvent(new KeyboardEvent("keydown", {key:"Escape", code:"Escape", bubbles:true}));
    }
    return !!option;
  }
  function radio(value) {
    const material = [...document.querySelectorAll("mat-radio-button")].find(node => {
      const label = node.querySelector(".mat-radio-label-content");
      return visible(node) && norm(label?.innerText || node.innerText).replace(/ information$/, "") === norm(value);
    });
    if (material) {
      const input = material.querySelector("input[type=radio]");
      if (!input?.checked) (material.querySelector("label") || material).click();
      return !!input?.checked;
    }
    const label = labels().find(node => visible(node) && text(node) === norm(value));
    const control = label?.control || label?.querySelector("input[type=radio]") || label;
    if (!visible(control)) return false;
    if (control instanceof HTMLInputElement && control.checked) return true;
    if (control.getAttribute("aria-checked") === "true") return true;
    control.click();
    return !(control instanceof HTMLInputElement) || control.checked;
  }
  function mark(label, ok) { (ok ? done : pending).push(label); }
  function finish(needsDate = false, needsCertificate = false) {
    if (supplied) return {done, pending, needsDate, needsCertificate};
    alert((done.length ? "Filled: " + done.join(", ") + ".\n\n" : "") +
      (pending.length ? "Check or complete: " + pending.join(", ") + ".\n\n" : "") +
      "Review the portal fields before requesting or entering the OTP.");
  }
  async function pickDate(input, iso) {
    if (!input?.readOnly) return false;
    const [year, month, day] = iso.split("-").map(Number);
    const target = new Date(year, month - 1, day);
    let calendar = [...document.querySelectorAll("mat-calendar")].find(visible);
    if (!calendar) {
      const toggle = input.closest(".signingDate,mat-form-field")?.querySelector("mat-datepicker-toggle button");
      (toggle || input).click();
      calendar = await until(() => [...document.querySelectorAll("mat-calendar")].find(visible), 8);
    }
    if (!calendar) return false;
    const period = calendar.querySelector(".mat-calendar-period-button");
    const previous = calendar.querySelector(".mat-calendar-previous-button");
    const next = calendar.querySelector(".mat-calendar-next-button");
    const format = new Intl.DateTimeFormat("en", {month:"short", year:"numeric"});
    for (let i = 0; i < 36; i++) {
      const current = norm(period?.innerText);
      if (current.startsWith(norm(format.format(target)))) {
        const cell = [...calendar.querySelectorAll(".mat-calendar-body-cell")].find(node =>
          !node.disabled && node.getAttribute("aria-disabled") !== "true" && Number(node.innerText.trim()) === day);
        if (!cell) return false;
        cell.click();
        await pause(300);
        return input.value === iso.split("-").reverse().join("-");
      }
      const displayed = new Date((period?.innerText || "").trim() + " 1");
      if (isNaN(displayed)) break;
      const button = displayed > target ? previous : next;
      if (!button || button.disabled) break;
      button.click();
      await pause(120);
    }
    input.dispatchEvent(new KeyboardEvent("keydown", {key:"Escape", bubbles:true}));
    return false;
  }
  const signing = find(/date of signing|signing date|signingdate|dateofsigning|signed date|dd mm yyyy/, inputSelector) ||
    [...document.querySelectorAll("input[type=date]")].filter(visible)[0];
  const calendarDate = data.signed_iso.split("-").reverse().join("-");
  const dateInput = () => document.querySelector('input[formcontrolname="signingDate"]');
  const ensureDate = async () => {
    const input = dateInput();
    if (!input || input.value === calendarDate) return true;
    await pickDate(input, data.signed_iso);
    return !!await until(() => dateInput()?.value === calendarDate, 6);
  };
  mark("Signing date", (dateInput() && await ensureDate()) ||
    set(signing, signing?.type === "date" ? data.signed_iso : calendarDate));
  if (pending.length) return finish(!!dateInput()?.readOnly);
  mark("Firm registration number", await choice(/firm registration|\bfrn\b/, data.frn,
    document.querySelector('ng-select[formcontrolname="FRN"]')));
  if (pending.length) return finish();
  mark("Document type", await until(() => radio("Certificates and Other Reports")));
  if (pending.length) return finish();
  if (!await ensureDate()) {
    pending.push("Signing date");
    return finish(true);
  }
  const certificate = document.querySelector('ng-select[formcontrolname="certficateType"]');
  const selectedCertificate = certificate?.querySelector(".ng-value-label")?.textContent?.trim();
  mark("Certificate type", (data.accept_portal_certificate && selectedCertificate) ||
    await choice(/type of certificate|certificate type|certficatetype/, data.subtype, certificate, true));
  if (pending.length) return finish(false, !!certificate);
  await pause(400);
  if (!await ensureDate()) {
    pending.push("Signing date");
    return finish(true);
  }
  mark("Figures mode", await until(() => radio("Numeric and Alphanumeric")));
  if (pending.length) return finish();
  let particulars = [];
  for (let attempt = 0; attempt < 20 && particulars.length < 2; attempt++) {
    particulars = [...document.querySelectorAll(inputSelector)].filter(node =>
    visible(node) && (/particular/.test(norm(node.placeholder)) ||
      /particular|udinprtclname/.test(norm([node.name,node.id,node.getAttribute("formcontrolname"),node.getAttribute("aria-label")].join(" "))) ||
      /^(net worth|networth) in /.test(norm(node.value))));
    if (particulars.length < 2) await pause(250);
  }
  const denominations = [];
  for (const [index, figure] of data.figures.entries()) {
    const field = particulars[index];
    let row = field?.closest(".particularsForm[formgroupname],.particularsForm,tr,[role=row]");
    if (!row && field) {
      let parent = field.parentElement;
      while (parent && !parent.contains(particulars[index ? 0 : 1])) {
        if ([...parent.querySelectorAll(inputSelector)].filter(visible).length >= 2) {
          row = parent;
          break;
        }
        parent = parent.parentElement;
      }
    }
    const other = row ? [...row.querySelectorAll(inputSelector)].filter(node => visible(node) && node !== field) : [];
    const value = other.find(node => node.getAttribute("formcontrolname") === "figureValue") ||
      other.find(node => /figure|value|amount/.test(norm(node.placeholder || node.name))) ||
      (other.length === 1 ? other[0] : null);
    const denomination = row?.querySelector('[formcontrolname="denominationValue"]') ||
      (row && [...row.querySelectorAll("select")].find(node =>
        [...node.options].some(option => norm(option.textContent) === "actual")));
    const labelOK = field?.value === figure.particulars || set(field, figure.particulars);
    const valueOK = value?.value === figure.figure || set(value, figure.figure);
    mark(figure.particulars, labelOK && valueOK);
    if (visible(denomination)) denominations.push({denomination, figure});
  }
  for (const {denomination, figure} of denominations) {
    mark(figure.particulars + " denomination", await choice(/denomination/, "Actual", denomination));
  }
  const description = document.querySelector('textarea[formcontrolname="desc"]') ||
    find(/document description|documentdescription/, "textarea,input") ||
    [...document.querySelectorAll("textarea")].filter(visible)[0];
  mark("Document description", set(description, data.description));
  if (dateInput() && dateInput().value !== calendarDate) {
    pending.push("Signing date");
    return finish(true);
  }
  return finish();
})
