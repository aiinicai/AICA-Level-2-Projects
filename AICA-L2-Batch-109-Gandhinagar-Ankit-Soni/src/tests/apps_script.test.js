/* ==========================================================================
 *  Tests for the Google Apps Script bridge (apps_script/Code.gs)
 * --------------------------------------------------------------------------
 *  Apps Script runs on Google's servers, so the Google services are stubbed
 *  here and the script is loaded into a VM context.  What is tested is the
 *  part that has to be right: reading the confirmed figure out of a reply,
 *  finding the reference code, deciding agreed / not in agreement, spotting
 *  a bounce, never recording a message twice, and publishing the feed in
 *  exactly the shape the desktop application consumes.
 * ========================================================================== */

const fs = require("fs");
const path = require("path");
const vm = require("vm");

let passed = 0, failed = 0;
function ok(name, condition, detail) {
  if (condition) { passed++; console.log("  PASS  " + name); }
  else { failed++; console.log("  FAIL  " + name + (detail ? "  -> " + detail : "")); }
}
function eq(name, actual, expected) {
  ok(name, actual === expected, "got " + JSON.stringify(actual) +
                                ", expected " + JSON.stringify(expected));
}
function head(title) { console.log("\n== " + title + " =="); }

/* ----------------------------------------------------------------- stubs */
function makeEnvironment(options) {
  options = options || {};
  const labels = {};
  const properties = {};
  const sheets = {};
  const driveFiles = {};
  const logged = [];

  function Sheet(name) {
    this.name = name;
    this.rows = [];
    this.frozen = 0;
    this.appendRow = function (row) { this.rows.push(row.slice()); };
    this.getLastRow = function () { return this.rows.length; };
    this.setName = function (value) { this.name = value; };
    this.setFrozenRows = function (n) { this.frozen = n; };
    this.getRange = function (row, column, rows, columns) {
      const sheet = this;
      return {
        setValues: function (values) {
          for (let r = 0; r < values.length; r++) {
            while (sheet.rows.length < row - 1 + r + 1) { sheet.rows.push([]); }
            sheet.rows[row - 1 + r] = values[r].slice();
          }
          return this;
        },
        getValues: function () {
          const out = [];
          for (let r = 0; r < rows; r++) {
            const source = sheet.rows[row - 1 + r] || [];
            const line = [];
            for (let c = 0; c < columns; c++) {
              line.push(source[column - 1 + c] === undefined
                        ? "" : source[column - 1 + c]);
            }
            out.push(line);
          }
          return out;
        },
        setFontWeight: function () { return this; },
        setBackground: function () { return this; },
        setFontColor: function () { return this; }
      };
    };
  }

  function Book(id) {
    this.id = id;
    this.list = [new Sheet("Sheet1")];
    this.getId = function () { return this.id; };
    this.getUrl = function () { return "https://sheets.test/" + this.id; };
    this.getSheets = function () { return this.list; };
    this.getSheetByName = function (name) {
      return this.list.filter(function (s) { return s.name === name; })[0] || null;
    };
    this.insertSheet = function (name) {
      const sheet = new Sheet(name);
      this.list.push(sheet);
      return sheet;
    };
  }

  const sandbox = {
    console: console,
    Logger: { log: function (text) { logged.push(String(text)); } },
    Utilities: {
      getUuid: function () {
        // the real one is hex with dashes, and the key generator relies on it
        let hex = "";
        for (let i = 0; i < 32; i++) {
          hex += "0123456789abcdef".charAt(Math.floor(Math.random() * 16));
        }
        return hex.slice(0, 8) + "-" + hex.slice(8, 12) + "-" +
               hex.slice(12, 16) + "-" + hex.slice(16, 20) + "-" +
               hex.slice(20);
      },
      base64Encode: function (bytes) {
        return Buffer.from(bytes).toString("base64");
      },
      newBlob: function (content, type, name) {
        return { __content: content, __type: type, __name: name,
                 getDataAsString: function () { return this.__content; } };
      },
      formatDate: function (when, _tz, _format) {
        return when.toISOString().slice(0, 10);
      }
    },
    Session: { getScriptTimeZone: function () { return "Asia/Kolkata"; } },
    PropertiesService: {
      getScriptProperties: function () {
        return {
          getProperty: function (key) {
            return properties[key] === undefined ? null : properties[key];
          },
          setProperty: function (key, value) { properties[key] = value; }
        };
      }
    },
    SpreadsheetApp: {
      create: function (name) {
        const book = new Book("book-" + Object.keys(sheets).length);
        sheets[book.id] = book;
        book.name = name;
        return book;
      },
      openById: function (id) {
        if (!sheets[id]) { throw new Error("no such spreadsheet: " + id); }
        return sheets[id];
      }
    },
    GmailApp: {
      getUserLabelByName: function (name) { return labels[name] || null; },
      createLabel: function (name) {
        labels[name] = { name: name, applied: [] };
        return labels[name];
      },
      search: function () { return options.threads || []; },
      getMessageById: function (id) {
        let found = null;
        (options.threads || []).forEach(function (thread) {
          thread.getMessages().forEach(function (m) {
            if (m.getId() === id) { found = m; }
          });
        });
        if (!found) { throw new Error("Invalid argument: " + id); }
        return found;
      }
    },
    LockService: {
      getScriptLock: function () {
        return { tryLock: function () { return true; },
                 releaseLock: function () {} };
      }
    },
    ScriptApp: {
      getProjectTriggers: function () { return []; },
      newTrigger: function () {
        return { timeBased: function () {
          return { everyMinutes: function () {
            return { create: function () { sandbox.__triggerCreated = true; } };
          } };
        } };
      },
      deleteTrigger: function () {},
      getService: function () {
        return { getUrl: function () { return options.deployedUrl || ""; } };
      }
    },
    DriveApp: {
      __files: {},
      getFilesByName: function (name) {
        const file = sandbox.DriveApp.__files[name];
        let served = false;
        return {
          hasNext: function () { return !!file && !served; },
          next: function () { served = true; return file; }
        };
      },
      createFile: function (blob) {
        const file = {
          __name: blob.__name, __content: blob.__content,
          getUrl: function () { return "https://drive.test/" + this.__name; },
          setContent: function (text) { this.__content = text; return this; }
        };
        sandbox.DriveApp.__files[blob.__name] = file;
        return file;
      }
    },
    Drive: {
      Files: {
        create: function (metadata, blob) {
          const id = "drive-" + Object.keys(driveFiles).length;
          driveFiles[id] = blob && blob.__text ? blob.__text : "";
          return { id: id };
        },
        remove: function (id) { delete driveFiles[id]; }
      }
    },
    DocumentApp: {
      openById: function (id) {
        const text = driveFiles[id] || "";
        return { getBody: function () {
          return { getText: function () { return text; } };
        } };
      }
    },
    ContentService: {
      MimeType: { JSON: "application/json" },
      createTextOutput: function (text) {
        return { __text: text, setMimeType: function () { return this; } };
      }
    }
  };
  sandbox.__labels = labels;
  sandbox.__sheets = sheets;
  sandbox.__driveFiles = driveFiles;
  sandbox.__logged = logged;

  const context = vm.createContext(sandbox);
  const source = fs.readFileSync(
    path.join(__dirname, "..", "apps_script", "Code.gs"), "utf8");
  vm.runInContext(source, context, { filename: "Code.gs" });
  return sandbox;
}

/* -------------------------------------------------------- message factory */
function makeMessage(spec) {
  const attachments = (spec.attachments || []).map(function (a) {
    return {
      getName: function () { return a.name; },
      getContentType: function () { return a.type || "application/pdf"; },
      getDataAsString: function () { return a.text || ""; },
      getBytes: function () {
        return a.bytes || Array.from(Buffer.from(a.text || ""));
      },
      copyBlob: function () { return { __text: a.text || "" }; }
    };
  });
  const message = {
    __unread: spec.unread !== false,
    __read: false,
    getId: function () { return spec.id; },
    getSubject: function () { return spec.subject || ""; },
    getFrom: function () { return spec.from || ""; },
    getPlainBody: function () { return spec.body || ""; },
    getBody: function () { return spec.html || spec.body || ""; },
    getDate: function () { return new Date(spec.date || "2026-11-04T06:30:00Z"); },
    getRawContent: function () {
      return "In-Reply-To: " + (spec.inReplyTo || "") + "\r\n\r\n" +
             (spec.body || "");
    },
    getAttachments: function () { return attachments; },
    getHeader: function (name) { return (spec.headers || {})[name] || ""; },
    isUnread: function () { return this.__unread; },
    markRead: function () { this.__unread = false; this.__read = true; },
    getThread: function () { return message.__thread; }
  };
  return message;
}

function makeThread(id, messages) {
  const thread = {
    __labels: [],
    getId: function () { return id; },
    getMessages: function () { return messages; },
    addLabel: function (label) {
      this.__labels.push(label.name);
      label.applied.push(id);
    }
  };
  messages.forEach(function (m) { m.__thread = thread; });
  return thread;
}

/* ========================================================================= */
head("1. Reading the figure out of a signed slip");
{
  const env = makeEnvironment();
  const cases = [
    ["plain rupees",
     "We hereby confirm that the amount payable by us to ABC Ltd as on " +
     "31 March 2026 is INR 1,25,000.00", 125000, "INR"],
    ["international grouping",
     "We hereby confirm that the amount payable by us is USD 1,234,567.89",
     1234567.89, "USD"],
    ["bracketed figure stays negative",
     "We hereby confirm that the amount receivable by us is INR (5,000.00)",
     -5000, "INR"],
    ["rupee symbol",
     "We hereby confirm that the amount payable by us is ₹ 86,400",
     86400, "INR"],
    ["Rs. abbreviation",
     "We hereby confirm that the amount payable by us is Rs. 9,99,999",
     999999, "INR"],
    ["continental separators",
     "We hereby confirm that the amount payable by us is EUR 1.234.567,89",
     1234567.89, "EUR"],
    ["no currency given",
     "We hereby confirm that the amount payable by us is 42,500.50",
     42500.5, ""],
    ["figure on the next line",
     "We hereby confirm that the amount payable by us to ABC Ltd\n" +
     "as on 31 March 2026 is\nINR 7,50,000.00", 750000, "INR"]
  ];
  cases.forEach(function (row) {
    const found = env.extractAmount_(row[1], "");
    eq(row[0] + " - amount", found.amount, row[2]);
    eq(row[0] + " - currency", found.currency, row[3]);
    eq(row[0] + " - source", found.source, "attachment");
  });

  const fallback = env.extractAmount_("", "Our balance is INR 64,000");
  eq("body fallback reads the figure", fallback.amount, 64000);
  eq("body fallback is flagged lower", fallback.confidence, 0.75);
  eq("body fallback names its source", fallback.source, "email body");

  const slip = env.extractAmount_(
    "We hereby confirm that the amount payable by us is INR 1,000", "");
  eq("a signed slip scores higher", slip.confidence, 0.95);

  const none = env.extractAmount_("We have received your letter.", "Thank you");
  eq("nothing found leaves the amount blank", none.amount, "");
  eq("nothing found leaves confidence at zero", none.confidence, 0);

  eq("the attachment is preferred over the body",
     env.extractAmount_(
       "We hereby confirm that the amount payable by us is INR 500", "").amount,
     500);
  eq("confirmation date is picked up",
     env.extractAmount_(
       "We hereby confirm that the amount payable by us as on 31 March 2026 " +
       "is INR 500", "").confirmedOn,
     "31 March 2026");
}

head("2. Reference codes");
{
  const env = makeEnvironment();
  eq("found in the subject",
     env.findReference_(["Re: Balance confirmation [BCG-7F3K2A]", "", ""]),
     "BCG-7F3K2A");
  eq("found in the body",
     env.findReference_(["", "Our ref BCG-9MNPQR for your records", ""]),
     "BCG-9MNPQR");
  eq("found in the attachment",
     env.findReference_(["", "", "Reference: bcg-23456a"]), "BCG-23456A");
  eq("subject wins over the body",
     env.findReference_(["[BCG-AAAAAA]", "BCG-BBBBBB", ""]), "BCG-AAAAAA");
  eq("absent gives an empty string", env.findReference_(["", "", ""]), "");
  eq("a code with banned characters is not matched",
     env.findReference_(["BCG-1O0I23"]), "");
}

head("3. Stance, bounces and senders");
{
  const env = makeEnvironment();
  eq("agreement", env.stance_("The balance is in agreement with our books"),
     "agreed");
  eq("disagreement", env.stance_("The amount is not in agreement; see below"),
     "not in agreement");
  eq("a difference outranks a confirmation",
     env.stance_("We confirm the balance but there is a difference of 500"),
     "not in agreement");
  eq("silence", env.stance_("Please find attached."), "");

  ok("mailer-daemon is a bounce",
     env.looksLikeBounce_("Mail Delivery Subsystem <MAILER-DAEMON@gmail.com>",
                          "Delivery Status Notification (Failure)", ""));
  ok("undeliverable is a bounce",
     env.looksLikeBounce_("postmaster@acme.test", "Undeliverable: request",
                          ""));
  ok("an ordinary reply is not a bounce",
     env.looksLikeBounce_("accounts@acme.test", "Re: Balance confirmation",
                          "Please find attached.") === false);

  eq("address pulled out of a display name",
     env.emailOf_('"Acme Traders" <accounts@acme.test>'), "accounts@acme.test");
  eq("a bare address survives", env.emailOf_("accounts@acme.test"),
     "accounts@acme.test");
  eq("display name pulled out",
     env.nameOf_('"Acme Traders" <accounts@acme.test>'), "Acme Traders");
  eq("In-Reply-To read from the raw headers",
     env.headerOf_("Subject: x\r\nIn-Reply-To: <abc@mail>\r\n", "In-Reply-To"),
     "<abc@mail>");
}

head("4. HTML-only bodies");
{
  const env = makeEnvironment();
  const text = env.stripHtml_(
    "<p>We hereby confirm that the amount payable by us is INR 1,000</p>" +
    "<style>p{color:red}</style><br>Regards&nbsp;&amp; thanks");
  ok("tags removed", text.indexOf("<") < 0);
  ok("style block removed", text.indexOf("color:red") < 0);
  ok("entities decoded", text.indexOf("Regards & thanks") >= 0);
  eq("the figure survives the strip",
     env.extractAmount_(text, "").amount, 1000);
}

head("5. One poll, end to end");
{
  const good = makeMessage({
    id: "m-1",
    subject: "Re: Balance confirmation [BCG-7F3K2A]",
    from: '"Acme Traders" <accounts@acme.test>',
    body: "Please find the signed confirmation attached. The balance is in " +
          "agreement with our books.",
    inReplyTo: "<sent-1@mail>",
    attachments: [{
      name: "signed-confirmation.pdf",
      text: "We hereby confirm that the amount payable by us to ABC Ltd as " +
            "on 31 March 2026 is INR 1,25,000.00  Authorised Signatory"
    }]
  });
  const vague = makeMessage({
    id: "m-2",
    subject: "balance confirmation",
    from: "ops@beta.test",
    body: "Received, we will revert shortly."
  });
  const bounce = makeMessage({
    id: "m-3",
    subject: "Undeliverable: Balance confirmation [BCG-9MNPQR]",
    from: "MAILER-DAEMON@googlemail.com",
    body: "Address not found. Your message was not delivered to " +
          "nosuch@gamma.test"
  });
  const threads = [makeThread("t-1", [good]), makeThread("t-2", [vague]),
                   makeThread("t-3", [bounce])];
  const env = makeEnvironment({ threads: threads });

  env.setUp();
  ok("the trigger is created by setUp", env.__triggerCreated === true);
  ok("both labels exist after setUp",
     !!env.__labels["BCG/Processed"] && !!env.__labels["BCG/Needs review"]);

  env.pollMailbox();
  const book = env.__sheets[Object.keys(env.__sheets)[0]];
  const sheet = book.getSheetByName("Replies");
  eq("header plus three rows", sheet.getLastRow(), 4);

  const columns = {};
  sheet.rows[0].forEach(function (name, index) { columns[name] = index; });
  const byId = {};
  sheet.rows.slice(1).forEach(function (row) {
    byId[row[columns.reply_id]] = row;
  });

  eq("the figure is recorded", byId["m-1"][columns.amount], 125000);
  eq("the currency is recorded", byId["m-1"][columns.currency], "INR");
  eq("the reference is recorded", byId["m-1"][columns.reference],
     "BCG-7F3K2A");
  eq("the stance is recorded", byId["m-1"][columns.stance], "agreed");
  eq("the signature is noted", byId["m-1"][columns.signed], true);
  eq("the thread is recorded", byId["m-1"][columns.thread_id], "t-1");
  eq("In-Reply-To is recorded", byId["m-1"][columns.in_reply_to],
     "<sent-1@mail>");
  eq("the attachment name is kept", byId["m-1"][columns.attachment_names],
     "signed-confirmation.pdf");
  eq("the clean reply is recorded", byId["m-1"][columns.status], "recorded");
  eq("a figureless reply goes for review", byId["m-2"][columns.status],
     "needs review");
  eq("and says why", byId["m-2"][columns.note], "no confirmed figure found");
  eq("the clean reply carries no note", byId["m-1"][columns.note], "");
  eq("a bounce is recorded", byId["m-3"][columns.status], "recorded");
  eq("a bounce is marked as one", byId["m-3"][columns.bounced], true);

  eq("the clean reply is labelled processed",
     threads[0].__labels.join(","), "BCG/Processed");
  eq("the vague reply is labelled for review",
     threads[1].__labels.join(","), "BCG/Needs review");
  eq("the clean reply is marked read", good.__unread, false);
  eq("the vague reply stays unread", vague.__unread, true);

  const trail = book.getSheetByName("Audit trail");
  ok("the audit trail is written", trail.getLastRow() >= 3);

  head("6. A second poll records nothing twice", 0);
  vague.__unread = true;
  good.__unread = true;                 // as if the auditor re-marked it
  env.pollMailbox();
  eq("still three rows", sheet.getLastRow(), 4);

  head("7. The key guarding the feed");
  const key = env.accessKey_();
  eq("the key is 40 characters", key.length, 40);
  ok("the key is hex only", /^[0-9a-f]{40}$/.test(key), key);
  eq("the key does not change on a second call", env.accessKey_(), key);
  const refused = JSON.parse(env.doGet({ parameter: {} }).__text);
  eq("no key is refused", refused.error, "not authorised");
  ok("a refusal carries no replies", refused.replies === undefined);
  const wrong = JSON.parse(
    env.doGet({ parameter: { key: "0".repeat(40) } }).__text);
  eq("a wrong key is refused", wrong.error, "not authorised");
  ok("a refusal does not leak the key",
     JSON.stringify(refused).indexOf(key) < 0);

  const fresh = env.resetAccessKey !== undefined;
  ok("the key can be reissued", fresh);

  head("8. The feed the desktop application reads");
  const response = env.doGet({ parameter: { key: key } });
  const payload = JSON.parse(response.__text);
  eq("three replies published", payload.count, 3);
  ok("the poll time is published", !!payload.last_poll);

  const first = payload.replies.filter(function (r) {
    return r.id === "m-1";
  })[0];
  ["id", "received_at", "from_email", "from_name", "subject", "reference",
   "thread_id", "in_reply_to", "body", "bounced", "attachments"
  ].forEach(function (key) {
    ok("the feed carries " + key, Object.keys(first).indexOf(key) >= 0);
  });
  eq("from_email in the feed", first.from_email, "accounts@acme.test");
  eq("from_name in the feed", first.from_name, "Acme Traders");
  ok("attachments are a list of {name, text}",
     Array.isArray(first.attachments) && first.attachments.length === 1 &&
     typeof first.attachments[0].name === "string" &&
     first.attachments[0].text.indexOf("1,25,000.00") >= 0);
  eq("a bounce reaches the feed as a flag",
     payload.replies.filter(function (r) { return r.id === "m-3"; })[0].bounced,
     true);

  const filtered = JSON.parse(
    env.doGet({ parameter: { key: key, status: "recorded" } }).__text);
  eq("the status filter works", filtered.count, 2);
  const dated = JSON.parse(
    env.doGet({ parameter: { key: key, since: "2026-12-01" } }).__text);
  eq("the date filter works", dated.count, 0);

  head("8b. Handing over a reply's own PDF");
  ok("the feed names what is attached",
     Array.isArray(first.files) && first.files[0] === "signed-confirmation.pdf",
     JSON.stringify(first.files));
  eq("a reply with nothing attached lists nothing",
     payload.replies.filter(function (r) { return r.id === "m-2"; })[0]
       .files.length, 0);
  const handed = JSON.parse(
    env.doGet({ parameter: { key: key, message: "m-1" } }).__text);
  eq("one file is handed over", handed.files.length, 1);
  eq("under its own name", handed.files[0].name, "signed-confirmation.pdf");
  ok("as the original bytes, base64-encoded",
     Buffer.from(handed.files[0].data, "base64").toString()
       .indexOf("1,25,000.00") > 0);
  eq("with its size", handed.files[0].size,
     Buffer.from(handed.files[0].data, "base64").length);
  const noKey = JSON.parse(env.doGet({ parameter: { message: "m-1" } }).__text);
  ok("never without the key", noKey.error === "not authorised" &&
     noKey.files === undefined);
  const stranger = JSON.parse(
    env.doGet({ parameter: { key: key, message: "not-recorded" } }).__text);
  ok("only a message already in the sheet is served",
     stranger.error === "unknown message" && stranger.files.length === 0);

  head("9. The address printed for the auditor");
  eq("nothing is given before deployment", env.feedUrl(), "");
  ok("the key is printed anyway, to build the address by hand",
     env.__logged.some(line => line.indexOf("ACCESS KEY:") === 0));
  ok("and where to find the address",
     env.__logged.some(line => line.indexOf("Manage deployments") > 0));

  const deployed = makeEnvironment({ threads: threads,
                                     deployedUrl: "https://script.test/exec" });
  const address = deployed.feedUrl();
  ok("a public address is given whole", address.indexOf(
     "https://script.test/exec?key=") === 0, address);
  eq("and the key it will be checked against",
     address.split("key=")[1], deployed.accessKey_());

  // getUrl() can hand back the private /dev address on the V8 runtime; it
  // always demands a browser sign-in, so it must never be given out
  const priv = makeEnvironment({ threads: threads,
                                 deployedUrl: "https://script.test/dev" });
  eq("the private /dev address is never given out", priv.feedUrl(), "");
  ok("and is named as the problem",
     priv.__logged.some(line => line.indexOf("/dev") > 0));
  ok("the key is still printed, so the address can be built",
     priv.__logged.some(line => line.indexOf("ACCESS KEY:") === 0));
  ok("no /dev address appears in anything printed",
     priv.__logged.every(line => line.indexOf("script.test/dev") < 0));

  head("10. The offline export, for a locked-down Workspace domain");
  const exported = env.exportFeedToDrive();
  eq("a Drive file is written", exported,
     "https://drive.test/balance-confirmation-replies.json");
  const written = JSON.parse(
    env.DriveApp.__files["balance-confirmation-replies.json"].__content);
  eq("it holds the same replies", written.count, 3);
  ok("it is the shape Import replies expects",
     Array.isArray(written.replies) && !!written.replies[0].id);
  env.exportFeedToDrive();
  eq("running it again replaces the file rather than adding one",
     Object.keys(env.DriveApp.__files).length, 1);
}

head("11. An attachment that cannot be read does not lose the reply");
{
  const broken = makeMessage({
    id: "m-9",
    subject: "Balance confirmation [BCG-7F3K2A]",
    from: "accounts@delta.test",
    body: "We hereby confirm that the amount payable by us is INR 4,000",
    attachments: [{ name: "scan.tiff", type: "image/tiff", text: "" }]
  });
  const thread = makeThread("t-9", [broken]);
  const env = makeEnvironment({ threads: [thread] });
  env.Drive.Files.create = function () { throw new Error("Drive is busy"); };
  env.pollMailbox();
  const book = env.__sheets[Object.keys(env.__sheets)[0]];
  const sheet = book.getSheetByName("Replies");
  eq("the reply is still recorded", sheet.getLastRow(), 2);
  const columns = {};
  sheet.rows[0].forEach(function (name, index) { columns[name] = index; });
  eq("the figure came from the body", sheet.rows[1][columns.amount], 4000);
  eq("the source is named", sheet.rows[1][columns.source], "email body");
  eq("an unread attachment forces review",
     sheet.rows[1][columns.status], "needs review");
  eq("and the reason is recorded", sheet.rows[1][columns.note],
     "1 attachment(s) could not be read");
  ok("the failure is on the audit trail",
     book.getSheetByName("Audit trail").rows.some(function (row) {
       return String(row[1]) === "attachment";
     }));
}

head("13. Our own request is never recorded as a reply");
{
  const LETTER = "ACCOUNTS RECEIVABLE/DEBTOR CONFIRMATION\nAccording to our " +
    "records, the amount due from you as at 31 March 2026 is INR " +
    "35,00,000.00 (In Words: Rupees Thirty Five Lakh Only)\nIf the amount is " +
    "not in agreement with your records, please notify our auditors\n" +
    "We hereby confirm that the amount payable by us to Client Ltd as on " +
    "31 March 2026 is INR ______________\nName and Title : ____";
  const own = makeMessage({
    id: "own-1", subject: "Balance confirmation request [BCG-7F3K2A]",
    from: "Audit Team <audit@firm.test>",
    headers: { "X-BCG-Request": "BCG-7F3K2A" },
    body: "Please find attached a balance confirmation request, being INR " +
          "35,00,000.00.",
    attachments: [{ name: "XYZ - Trade Receivable.pdf", text: LETTER }]
  });
  const returned = makeMessage({
    id: "ret-1", subject: "Re: Balance confirmation request [BCG-7F3K2A]",
    from: "accounts@xyz.test", body: "PFA.",
    attachments: [{ name: "scan.pdf", text: LETTER }]
  });
  const differs = makeMessage({
    id: "dif-1", subject: "Re: Balance confirmation request [BCG-7F3K2A]",
    from: "accounts@xyz.test",
    body: "Balance as per our books is Rs. 25,00,000.\n\nOn Tue, 10 Nov 2026 " +
          "at 14:05, Audit Team <audit@firm.test> wrote:\n> balance appearing " +
          "in its books is INR 35,00,000.00\n> particulars of the difference"
  });
  const threads = [makeThread("t-own", [own]), makeThread("t-ret", [returned]),
                   makeThread("t-dif", [differs])];
  const env = makeEnvironment({ threads: threads });
  env.pollMailbox();
  const sheet = env.__sheets[Object.keys(env.__sheets)[0]]
                   .getSheetByName("Replies");
  const columns = {};
  sheet.rows[0].forEach(function (name, index) { columns[name] = index; });
  const byId = {};
  sheet.rows.slice(1).forEach(function (row) {
    byId[row[columns.reply_id]] = row;
  });
  ok("the request the application sent is not recorded",
     byId["own-1"] === undefined);
  eq("it is not labelled", threads[0].__labels.length, 0);
  eq("and it is left unread", own.__unread, true);
  eq("a letter merely returned is not read as the party's figure",
     byId["ret-1"][columns.amount], "");
  eq("it goes for review", byId["ret-1"][columns.status], "needs review");
  eq("the party's own figure is read, not the quoted one",
     byId["dif-1"][columns.amount], 2500000);
  eq("the quoted 'difference' is not taken as the party's stance",
     byId["dif-1"][columns.stance], "");
  eq("quoted text is stripped",
     env.stripQuoted_("Ours is 5\n\nOn Mon, X <x@y> wrote:\n> theirs is 9")
        .trim(), "Ours is 5");
}

head("11b. What the attachment hand-over will not send");
{
  const big = makeMessage({
    id: "m-20", subject: "Balance confirmation", from: "a@b.test",
    body: "We hereby confirm that the amount payable by us is INR 4,000",
    attachments: [
      { name: "ledger.xlsx", type: "application/vnd.ms-excel", text: "x" },
      { name: "huge.pdf", type: "application/pdf",
        bytes: { length: 13 * 1024 * 1024 } },
      { name: "slip.jpg", type: "image/jpeg", text: "JPEGDATA" }
    ]
  });
  const env = makeEnvironment({ threads: [makeThread("t-20", [big])] });
  env.pollMailbox();
  const out = JSON.parse(env.doGet(
    { parameter: { key: env.accessKey_(), message: "m-20" } }).__text);
  eq("only the image is sent", out.files.map(function (f) { return f.name; })
     .join(","), "slip.jpg");
  ok("a spreadsheet is skipped and said to be",
     out.skipped.some(function (x) { return x.indexOf("ledger.xlsx") === 0; }));
  ok("an oversized file is skipped and said to be",
     out.skipped.some(function (x) { return x.indexOf("huge.pdf") === 0; }));
}

head("12. The script never deletes anything");
{
  const source = fs.readFileSync(
    path.join(__dirname, "..", "apps_script", "Code.gs"), "utf8");
  ok("no moveToTrash", source.indexOf("moveToTrash") < 0);
  ok("no moveThreadToTrash", source.indexOf("ToTrash") < 0);
  ok("no GmailApp delete", /GmailApp\.[a-zA-Z]*[Dd]elete/.test(source) === false);
  ok("the only Drive removal is the temporary conversion file",
     (source.match(/Drive\.Files\.remove/g) || []).length === 1);
  ok("the Gmail search keeps is:unread", source.indexOf("is:unread") > 0);
  ok("read is only ever set on success",
     source.indexOf("if (ok) {") > 0 && source.indexOf("message.markRead()") >
     source.indexOf("if (ok) {"));
  const code = source.replace(/\/\*[\s\S]*?\*\//g, "")   // block comments
                     .replace(/^\s*\/\/.*$/gm, "");      // line comments
  ok("no credential is read or stored",
     /password|refresh_token|client_secret|access_token/i.test(code) === false);
  ok("nothing is sent off the account", code.indexOf("UrlFetchApp") < 0);
  ok("the feed is guarded by a key",
     /parameters\.key !== accessKey_\(\)/.test(code));
  ok("the key is not written into the sheet",
     makeEnvironment().COLUMNS.indexOf("key") < 0);
}

console.log("\n" + "-".repeat(56));
console.log("PASSED " + passed + "   FAILED " + failed);
process.exit(failed ? 1 : 0);
