# Fair Share

Fair Share is a group expense sharing and bill splitting application designed to split group and personal expenses fairly with friends, roommates, and travel groups.

**Live app**: https://fairshare-rm.ai.studio/

## Architecture & Tech Stack

- **Frontend**: React 19, TanStack Router & Start, Tailwind CSS, shadcn/ui components.
- **Backend & Database**: Firebase Firestore & Firebase Auth with secure Firestore rules.
- **Balance Calculation Engine**: Pure integer-cent balancing logic (`src/lib/balanceEngine.ts`) ensuring penny-exact and testable splits.

## Development

You need Node.js and npm:

```sh
npm install
npm run dev
```
