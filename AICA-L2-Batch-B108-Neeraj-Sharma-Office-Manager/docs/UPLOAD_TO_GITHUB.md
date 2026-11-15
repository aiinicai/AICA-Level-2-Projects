# Put this project on GitHub (first time)
1. On github.com click **New repository**. Name it `audit-manager-desktop`. Choose **Private** (it holds your business software). Do NOT tick "Add a README".
2. Install Git for Windows (git-scm.com) if you do not have it.
3. Open the unzipped project folder, click the address bar, type `cmd`, press Enter, and run:

       git remote add origin https://github.com/YOUR-USERNAME/audit-manager-desktop.git
       git push -u origin main

   GitHub asks you to sign in in the browser the first time.
4. Never upload the `.db` database or backups: they hold client data. `.gitignore` already blocks them.
