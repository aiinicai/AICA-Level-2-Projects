import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { FIRM_INITIALS } from '@/lib/constants'

export default function NotFoundPage() {
  return (
    <div className="bg-background flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <div className="bg-primary text-primary-foreground grid size-12 place-items-center rounded-lg text-xs font-bold">
        {FIRM_INITIALS}
      </div>
      <div>
        <p className="text-3xl font-semibold">404</p>
        <p className="text-muted-foreground mt-1 text-sm">
          That page does not exist, or you no longer have access to it.
        </p>
      </div>
      <Button asChild>
        <Link to="/">Back to my workspace</Link>
      </Button>
    </div>
  )
}
