import type { FormEvent } from 'react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState, ErrorState, LoadingState } from '@/components/states';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table';
import { useAccounts, useCreateAccount, useUpdateAccountStatus } from '@/hooks/queries';

export default function AccountsPage() {
  const { t } = useTranslation();
  const accounts = useAccounts();
  const create = useCreateAccount();
  const updateStatus = useUpdateAccountStatus();

  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [company, setCompany] = useState('');

  const submit = (event: FormEvent) => {
    event.preventDefault();
    create.mutate(
      { phone_number: phone, password, company_name: company },
      {
        onSuccess: () => {
          setPhone('');
          setPassword('');
          setCompany('');
        },
      },
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
          <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ac-phone">{t('auth.phone')}</Label>
              <Input
                id="ac-phone"
                dir="ltr"
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
              <Label htmlFor="ac-password">{t('auth.password')}</Label>
              <Input
                id="ac-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" disabled={create.isPending}>
              {t('settings.add')}
            </Button>
          </form>
          {create.isError && <p className="mt-2 text-sm text-critical">{t('accounts.error')}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {accounts.isLoading ? (
            <LoadingState />
          ) : accounts.isError ? (
            <ErrorState onRetry={() => accounts.refetch()} />
          ) : (accounts.data ?? []).length === 0 ? (
            <EmptyState />
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>{t('accounts.company')}</TH>
                  <TH>{t('auth.phone')}</TH>
                  <TH>{t('accounts.role')}</TH>
                  <TH>{t('alerts.status')}</TH>
                  <TH />
                </TR>
              </THead>
              <TBody>
                {(accounts.data ?? []).map((account) => (
                  <TR key={account.id}>
                    <TD>{account.company_name}</TD>
                    <TD dir="ltr">{account.phone_number}</TD>
                    <TD className="text-fg-muted">{account.role}</TD>
                    <TD>{t(`accountStatus.${account.status}`)}</TD>
                    <TD className="text-end">
                      {account.role !== 'SUPER_ADMIN' && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={updateStatus.isPending}
                          onClick={() =>
                            updateStatus.mutate({
                              id: account.id,
                              status: account.status === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE',
                            })
                          }
                        >
                          {account.status === 'ACTIVE'
                            ? t('accounts.suspend')
                            : t('accounts.activate')}
                        </Button>
                      )}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
