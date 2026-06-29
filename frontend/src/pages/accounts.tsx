import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { EmptyState, ErrorState, LoadingState } from '@/components/states';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table';
import { useAccounts, useCreateAccount, useUpdateAccount } from '@/hooks/queries';
import { formatDateTime } from '@/lib/format';
import { useSettings } from '@/stores/settings';
import type { AccountSummary } from '@/types/api';

export default function AccountsPage() {
  const { t } = useTranslation();
  const locale = useSettings((state) => state.locale);
  const accounts = useAccounts();
  const create = useCreateAccount();
  const update = useUpdateAccount();

  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [company, setCompany] = useState('');
  const [contactEmail, setContactEmail] = useState('');

  const [search, setSearch] = useState('');

  const [editing, setEditing] = useState<AccountSummary | null>(null);
  const [editCompany, setEditCompany] = useState('');
  const [editEmail, setEditEmail] = useState('');

  const [confirmTarget, setConfirmTarget] = useState<{
    id: string;
    action: 'suspend' | 'activate';
    name: string;
  } | null>(null);

  const filtered = useMemo(() => {
    if (!search) return accounts.data ?? [];
    const q = search.toLowerCase();
    return (accounts.data ?? []).filter(
      (a) => a.company_name.toLowerCase().includes(q) || a.phone_number.includes(q),
    );
  }, [accounts.data, search]);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    create.mutate(
      {
        phone_number: phone,
        password,
        company_name: company,
        contact_email: contactEmail || undefined,
      },
      {
        onSuccess: () => {
          setPhone('');
          setPassword('');
          setCompany('');
          setContactEmail('');
        },
      },
    );
  };

  const openEdit = (account: AccountSummary) => {
    setEditing(account);
    setEditCompany(account.company_name);
    setEditEmail(account.contact_email ?? '');
  };

  const saveEdit = () => {
    if (!editing) return;
    update.mutate(
      { id: editing.id, company_name: editCompany, contact_email: editEmail || null },
      { onSuccess: () => setEditing(null) },
    );
  };

  const confirmAction = () => {
    if (!confirmTarget) return;
    update.mutate(
      {
        id: confirmTarget.id,
        status: confirmTarget.action === 'suspend' ? 'SUSPENDED' : 'ACTIVE',
      },
      { onSuccess: () => setConfirmTarget(null) },
    );
  };

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t('nav.accounts')}</h1>

      <Card>
        <CardHeader>
          <CardTitle>{t('accounts.create')}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ac-phone">{t('accounts.phone')}</Label>
              <Input
                id="ac-phone"
                dir="ltr"
                placeholder="+22200000000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ac-company">{t('accounts.company')}</Label>
              <Input
                id="ac-company"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ac-email">{t('accounts.contactEmail')}</Label>
              <Input
                id="ac-email"
                type="email"
                dir="ltr"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ac-password">{t('auth.password')}</Label>
              <Input
                id="ac-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="sm:col-span-2 lg:col-span-4">
              <Button type="submit" disabled={create.isPending}>
                {t('settings.add')}
              </Button>
            </div>
          </form>
          {create.isError && <p className="mt-2 text-sm text-critical">{t('accounts.error')}</p>}
          {create.isSuccess && (
            <p className="mt-2 text-sm text-normal">{t('accountsEdit.success')}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle>{t('nav.accounts')}</CardTitle>
          <Input
            placeholder={t('accounts.search')}
            className="sm:max-w-xs"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </CardHeader>
        <CardContent className="p-0">
          {accounts.isLoading ? (
            <LoadingState />
          ) : accounts.isError ? (
            <ErrorState onRetry={() => accounts.refetch()} />
          ) : filtered.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <THead>
                  <TR>
                    <TH>{t('accounts.company')}</TH>
                    <TH>{t('accounts.contactEmail')}</TH>
                    <TH>{t('accounts.phone')}</TH>
                    <TH>{t('accounts.role')}</TH>
                    <TH>{t('accounts.status')}</TH>
                    <TH>{t('accounts.lastLogin')}</TH>
                    <TH>{t('accounts.createdAt')}</TH>
                    <TH />
                  </TR>
                </THead>
                <TBody>
                  {filtered.map((account) => (
                    <TR key={account.id}>
                      <TD className="font-medium">{account.company_name}</TD>
                      <TD className="text-fg-muted">
                        {account.contact_email ? (
                          <span dir="ltr">{account.contact_email}</span>
                        ) : (
                          <span className="text-fg-muted/50">&mdash;</span>
                        )}
                      </TD>
                      <TD dir="ltr" className="font-mono text-sm text-fg-muted">
                        {account.phone_number}
                      </TD>
                      <TD>
                        <span className="text-fg-muted text-sm">{account.role}</span>
                      </TD>
                      <TD>
                        <span
                          className={
                            account.status === 'ACTIVE'
                              ? 'text-xs font-medium text-normal'
                              : 'text-xs font-medium text-critical'
                          }
                        >
                          {t(`accountStatus.${account.status}`)}
                        </span>
                      </TD>
                      <TD className="text-fg-muted text-sm whitespace-nowrap">
                        {account.last_login_at
                          ? formatDateTime(account.last_login_at, locale)
                          : '--'}
                      </TD>
                      <TD className="text-fg-muted text-sm whitespace-nowrap">
                        {formatDateTime(account.created_at, locale)}
                      </TD>
                      <TD className="text-end whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1">
                          {account.role !== 'SUPER_ADMIN' && (
                            <>
                              <Button size="sm" variant="ghost" onClick={() => openEdit(account)}>
                                {t('accounts.edit')}
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() =>
                                  setConfirmTarget({
                                    id: account.id,
                                    action: account.status === 'ACTIVE' ? 'suspend' : 'activate',
                                    name: account.company_name,
                                  })
                                }
                              >
                                {account.status === 'ACTIVE'
                                  ? t('accounts.suspend')
                                  : t('accounts.activate')}
                              </Button>
                            </>
                          )}
                        </div>
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent>
          <DialogTitle>{t('accountsEdit.title')}</DialogTitle>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="edit-company">{t('accountsEdit.companyName')}</Label>
              <Input
                id="edit-company"
                value={editCompany}
                onChange={(e) => setEditCompany(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="edit-email">{t('accountsEdit.contactEmail')}</Label>
              <Input
                id="edit-email"
                type="email"
                dir="ltr"
                value={editEmail}
                onChange={(e) => setEditEmail(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-1.5">
              <Label className="text-fg-muted text-sm">{t('accountsEdit.phoneNumber')}</Label>
              <span dir="ltr" className="text-sm">
                {editing?.phone_number}
              </span>
            </div>
            {update.isError && <p className="text-sm text-critical">{t('accounts.error')}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setEditing(null)}>
                {t('accounts.cancel')}
              </Button>
              <Button onClick={saveEdit} disabled={update.isPending}>
                {t('accounts.save')}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog
        open={confirmTarget !== null}
        onOpenChange={(open) => !open && setConfirmTarget(null)}
      >
        <DialogContent>
          <DialogTitle>
            {confirmTarget?.action === 'suspend'
              ? t('accounts.confirmSuspend')
              : t('accounts.confirmActivate')}
          </DialogTitle>
          <p className="text-sm text-fg-muted">
            {confirmTarget?.action === 'suspend'
              ? t('accounts.confirmSuspendDesc')
              : t('accounts.confirmActivateDesc')}
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setConfirmTarget(null)}>
              {t('accounts.cancel')}
            </Button>
            <Button onClick={confirmAction} disabled={update.isPending}>
              {confirmTarget?.action === 'suspend' ? t('accounts.suspend') : t('accounts.activate')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
