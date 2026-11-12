/**
 * Aeterna website enquiries -> Google Sheet (+ an email to the owner).
 *
 * Setup (once): open the sheet "Aeterna website enquiries" > Extensions > Apps Script, replace everything with
 * this file, Save, then Deploy > New deployment > type "Web app" > Execute as: Me > Who has access: Anyone >
 * Deploy > Authorize. Copy the Web app URL (ends in /exec) into LEAD_URL in site/app.html.
 * After editing this script later: Deploy > Manage deployments > edit > Version: New version (keeps the same URL).
 */
const NOTIFY = Session.getEffectiveUser().getEmail();   // the sheet owner's own address

function doPost(e) {
  const p = (e && e.parameter) || {};
  if (p.website) return reply_({ ok: true });            // hidden field only bots fill in
  // a leading = + - @ would make Sheets treat the text as a formula
  const clean = v => String(v || '').trim().replace(/^[=+\-@]/, "'$&").slice(0, 1500);
  const row = [
    Utilities.formatDate(new Date(), 'Asia/Kolkata', 'yyyy-MM-dd HH:mm'),
    clean(p.name), clean(p.phone), clean(p.email), clean(p.city),
    clean(p.interest), clean(p.message), clean(p.page), clean(p.source),
  ];
  if (!row[2] && !row[3]) return reply_({ ok: false, error: 'phone or email needed' });
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    SpreadsheetApp.getActiveSpreadsheet().getSheets()[0].appendRow(row);
  } finally {
    lock.releaseLock();
  }
  try {
    MailApp.sendEmail({
      to: NOTIFY,
      subject: 'New website enquiry: ' + (row[1] || row[2] || row[3]),
      body: ['Received', 'Name', 'Phone', 'Email', 'City', 'Interest', 'Message', 'Page', 'Source']
        .map((k, i) => k + ': ' + row[i]).join('\n') + '\n\n' + SpreadsheetApp.getActiveSpreadsheet().getUrl(),
    });
  } catch (err) { /* the row is saved even if the daily mail quota is used up */ }
  return reply_({ ok: true });
}

function doGet() { return reply_({ ok: true, service: 'aeterna-enquiries' }); }

function reply_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
