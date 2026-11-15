# Recording a demo video of Office Manager (Windows)
**Easiest: Xbox Game Bar (built in).** Open Office Manager, press `Win + G`, click the Capture (camera) widget, then Record. Stop with `Win + Alt + R`. Videos save in `Videos\Captures`. Tick the microphone to narrate.
**With your face in a corner (picture-in-picture):** use the free OBS Studio (obsproject.com): Sources > + > Window Capture (Office Manager) and + > Video Capture Device (webcam); drag the webcam small into a corner; Start Recording.
**Do this before recording:** run the app, create demo data only (fake clients), never show real client PAN/GSTIN or the Settings email password.
**Suggested 4-minute script:** 1 Dashboard and login > 2 Add a client / Excel import > 3 Bulk-create GST returns for a month > 4 Compliance calendar and Tasks board > 5 Create invoice, record payment, PDF > 6 Reports with your letterhead (PDF/Excel) > 7 WhatsApp bulk reminders > 8 Settings: logo, email, backup.
**To install and start from scratch on camera:** `pip install -r requirements.txt` then `python run_desktop.py`.
