import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Download, KeyRound, Trash2, UserCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import { api, apiPost } from '@/lib/api';
import { getErrorMessage } from '@/lib/utils';
import type { ChangePasswordRequest } from '@/types/api';

const passwordSchema = z
  .object({
    current_password: z.string().min(1, 'Requis'),
    new_password: z.string().min(12, '12 caractères minimum'),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, {
    message: 'Les mots de passe ne correspondent pas',
    path: ['confirm'],
  });

type PasswordForm = z.infer<typeof passwordSchema>;

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const { success, error, warning } = useToast();
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<PasswordForm>({ resolver: zodResolver(passwordSchema) });

  const onChangePassword = async (values: PasswordForm) => {
    try {
      const payload: ChangePasswordRequest = {
        current_password: values.current_password,
        new_password: values.new_password,
      };
      await apiPost('/users/me/password', payload);
      success('Mot de passe mis à jour');
      reset();
    } catch (err) {
      error('Échec', getErrorMessage(err));
    }
  };

  const onExport = async () => {
    setExporting(true);
    try {
      // RGPD : portabilité des données — l'API renvoie un JSON.
      const response = await api.get('/users/me/export', { responseType: 'blob' });
      const url = URL.createObjectURL(response.data as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `icy-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      success('Export téléchargé');
    } catch (err) {
      error('Export impossible', getErrorMessage(err));
    } finally {
      setExporting(false);
    }
  };

  const onDelete = async () => {
    if (!window.confirm('Supprimer définitivement votre compte ? Cette action est irréversible.')) {
      return;
    }
    setDeleting(true);
    try {
      await api.delete('/users/me');
      warning('Compte supprimé', 'Vous allez être déconnecté.');
      await logout();
    } catch (err) {
      error('Suppression impossible', getErrorMessage(err));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Paramètres</h1>
        <p className="text-sm text-muted-foreground">Profil, sécurité et droits RGPD.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <UserCircle2 className="h-4 w-4" /> Profil
          </CardTitle>
          <CardDescription>Informations associées à votre compte.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <Label>Adresse e-mail</Label>
            <p className="text-sm text-muted-foreground">{user?.email ?? '—'}</p>
          </div>
          <div className="flex flex-col gap-1">
            <Label>Rôle</Label>
            <p className="text-sm capitalize text-muted-foreground">{user?.role ?? '—'}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <KeyRound className="h-4 w-4" /> Mot de passe
          </CardTitle>
          <CardDescription>Choisissez un mot de passe long et unique.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleSubmit(onChangePassword)}
            className="grid gap-4 sm:grid-cols-2"
            noValidate
          >
            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <Label htmlFor="current_password">Mot de passe actuel</Label>
              <Input
                id="current_password"
                type="password"
                autoComplete="current-password"
                {...register('current_password')}
              />
              {errors.current_password && (
                <p className="text-xs text-destructive">{errors.current_password.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="new_password">Nouveau mot de passe</Label>
              <Input
                id="new_password"
                type="password"
                autoComplete="new-password"
                {...register('new_password')}
              />
              {errors.new_password && (
                <p className="text-xs text-destructive">{errors.new_password.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="confirm">Confirmation</Label>
              <Input
                id="confirm"
                type="password"
                autoComplete="new-password"
                {...register('confirm')}
              />
              {errors.confirm && (
                <p className="text-xs text-destructive">{errors.confirm.message}</p>
              )}
            </div>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={isSubmitting}>
                Mettre à jour
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Données personnelles (RGPD)</CardTitle>
          <CardDescription>
            Vous disposez d’un droit d’accès, de portabilité et d’oubli sur vos données.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium">Exporter mes données</p>
              <p className="text-xs text-muted-foreground">
                Téléchargement d’une archive JSON de votre profil et activité.
              </p>
            </div>
            <Button variant="outline" onClick={onExport} disabled={exporting}>
              <Download className="h-4 w-4" /> {exporting ? 'Préparation…' : 'Exporter'}
            </Button>
          </div>
          <Separator />
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-destructive">Supprimer mon compte</p>
              <p className="text-xs text-muted-foreground">
                Soft-delete + purge définitive sous 30 jours.
              </p>
            </div>
            <Button variant="destructive" onClick={onDelete} disabled={deleting}>
              <Trash2 className="h-4 w-4" /> {deleting ? 'Suppression…' : 'Supprimer'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
