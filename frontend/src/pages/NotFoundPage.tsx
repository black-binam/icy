import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <CardTitle className="text-3xl">404</CardTitle>
          <CardDescription>Cette page n’existe pas ou a été déplacée.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link to="/">Retour au tableau de bord</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
