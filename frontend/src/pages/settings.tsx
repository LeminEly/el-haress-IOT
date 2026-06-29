import { Trash2 } from 'lucide-react';
import type { FormEvent } from 'react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState, LoadingState } from '@/components/states';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectItem } from '@/components/ui/select';
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table';
import {
  useAlertRules,
  useCreateAlertRule,
  useCreateGateway,
  useDeleteAlertRule,
  useGateways,
  useSensors,
  useUpdateSensor,
} from '@/hooks/queries';
import type { AlertChannel, AlertCondition, AlertSeverity, Sensor } from '@/types/api';

const CHANNELS: AlertChannel[] = ['whatsapp', 'sms', 'email'];
const CONDITIONS: AlertCondition[] = ['GT', 'GTE', 'LT', 'LTE'];
const SEVERITIES: AlertSeverity[] = ['INFO', 'WARNING', 'CRITICAL', 'EMERGENCY'];

function GatewaysSection() {
  const { t } = useTranslation();
  const gateways = useGateways();
  const create = useCreateGateway();
  const [name, setName] = useState('');
  const [baseUrl, setBaseUrl] = useState('');

  const submit = (event: FormEvent) => {
    event.preventDefault();
    create.mutate(
      { name, base_url: baseUrl, poll_interval_seconds: 10 },
      {
        onSuccess: () => {
          setName('');
          setBaseUrl('');
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.gateways')}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {(gateways.data ?? []).map((gateway) => (
          <div key={gateway.id} className="flex items-center justify-between text-sm">
            <span>{gateway.name}</span>
            <span className="text-fg-subtle" dir="ltr">
              {gateway.base_url}
            </span>
          </div>
        ))}
        <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
          <div className="flex flex-1 flex-col gap-1.5">
            <Label htmlFor="gw-name">{t('settings.name')}</Label>
            <Input id="gw-name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="flex flex-1 flex-col gap-1.5">
            <Label htmlFor="gw-url">{t('settings.baseUrl')}</Label>
            <Input
              id="gw-url"
              dir="ltr"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              required
            />
          </div>
          <Button type="submit" disabled={create.isPending}>
            {t('settings.add')}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function SensorRow({ sensor }: { sensor: Sensor }) {
  const { t } = useTranslation();
  const update = useUpdateSensor();
  const [label, setLabel] = useState(sensor.label);
  return (
    <TR>
      <TD>
        <Input value={label} onChange={(e) => setLabel(e.target.value)} className="h-9" />
      </TD>
      <TD className="text-fg-muted">{sensor.kind}</TD>
      <TD>{sensor.is_active ? t('settings.active') : t('settings.inactive')}</TD>
      <TD className="text-end">
        <div className="flex justify-end gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={update.isPending}
            onClick={() => update.mutate({ id: sensor.id, label })}
          >
            {t('settings.save')}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => update.mutate({ id: sensor.id, is_active: !sensor.is_active })}
          >
            {sensor.is_active ? t('settings.disable') : t('settings.enable')}
          </Button>
        </div>
      </TD>
    </TR>
  );
}

function SensorsSection() {
  const { t } = useTranslation();
  const sensors = useSensors();
  if (sensors.isLoading) {
    return <LoadingState />;
  }
  const list = sensors.data ?? [];
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.sensors')}</CardTitle>
      </CardHeader>
      <CardContent>
        {list.length === 0 ? (
          <EmptyState message={t('dashboard.noSensors')} />
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>{t('settings.label')}</TH>
                <TH>{t('settings.kind')}</TH>
                <TH>{t('settings.state')}</TH>
                <TH />
              </TR>
            </THead>
            <TBody>
              {list.map((sensor) => (
                <SensorRow key={sensor.id} sensor={sensor} />
              ))}
            </TBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

function RulesSection() {
  const { t } = useTranslation();
  const rules = useAlertRules();
  const sensors = useSensors();
  const create = useCreateAlertRule();
  const remove = useDeleteAlertRule();

  const [name, setName] = useState('');
  const [sensorId, setSensorId] = useState('');
  const [condition, setCondition] = useState<AlertCondition>('GT');
  const [threshold, setThreshold] = useState('20');
  const [severity, setSeverity] = useState<AlertSeverity>('CRITICAL');
  const [cooldown, setCooldown] = useState('15');
  const [channels, setChannels] = useState<AlertChannel[]>(['email']);

  const toggleChannel = (channel: AlertChannel) =>
    setChannels((current) =>
      current.includes(channel)
        ? current.filter((value) => value !== channel)
        : [...current, channel],
    );

  const submit = (event: FormEvent) => {
    event.preventDefault();
    create.mutate(
      {
        name,
        sensor_id: sensorId || null,
        condition,
        threshold: Number(threshold),
        duration_seconds: 0,
        cooldown_minutes: Number(cooldown),
        severity,
        channels,
        is_active: true,
      },
      { onSuccess: () => setName('') },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.rules')}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {(rules.data ?? []).map((rule) => (
          <div key={rule.id} className="flex items-center justify-between gap-2 text-sm">
            <span className="truncate">
              {rule.name} — {t(`condition.${rule.condition}`)} {rule.threshold}
            </span>
            <Button
              size="icon"
              variant="ghost"
              aria-label={t('settings.delete')}
              onClick={() => remove.mutate(rule.id)}
            >
              <Trash2 className="size-4 text-critical" />
            </Button>
          </div>
        ))}

        <form onSubmit={submit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="rule-name">{t('settings.name')}</Label>
            <Input id="rule-name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>{t('settings.sensor')}</Label>
            <Select
              aria-label={t('settings.sensor')}
              value={sensorId || 'all'}
              onValueChange={(value) => setSensorId(value === 'all' ? '' : value)}
            >
              <SelectItem value="all">{t('settings.allSensors')}</SelectItem>
              {(sensors.data ?? []).map((sensor) => (
                <SelectItem key={sensor.id} value={sensor.id}>
                  {sensor.label}
                </SelectItem>
              ))}
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>{t('settings.condition')}</Label>
            <Select
              aria-label={t('settings.condition')}
              value={condition}
              onValueChange={(value) => setCondition(value as AlertCondition)}
            >
              {CONDITIONS.map((value) => (
                <SelectItem key={value} value={value}>
                  {t(`condition.${value}`)}
                </SelectItem>
              ))}
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="rule-threshold">{t('settings.threshold')}</Label>
            <Input
              id="rule-threshold"
              type="number"
              step="0.1"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>{t('settings.severity')}</Label>
            <Select
              aria-label={t('settings.severity')}
              value={severity}
              onValueChange={(value) => setSeverity(value as AlertSeverity)}
            >
              {SEVERITIES.map((value) => (
                <SelectItem key={value} value={value}>
                  {t(`severity.${value}`)}
                </SelectItem>
              ))}
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="rule-cooldown">{t('settings.cooldown')}</Label>
            <Input
              id="rule-cooldown"
              type="number"
              min="0"
              value={cooldown}
              onChange={(e) => setCooldown(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5 sm:col-span-2">
            <span className="text-sm font-medium text-fg">{t('settings.channels')}</span>
            <div className="flex flex-wrap gap-3">
              {CHANNELS.map((channel) => (
                <label key={channel} className="flex cursor-pointer items-center gap-2 text-sm">
                  <Checkbox
                    checked={channels.includes(channel)}
                    onCheckedChange={() => toggleChannel(channel)}
                  />
                  {t(`channel.${channel}`)}
                </label>
              ))}
            </div>
          </div>
          <div className="sm:col-span-2">
            <Button type="submit" disabled={create.isPending || channels.length === 0}>
              {t('settings.addRule')}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t('nav.settings')}</h1>
      <GatewaysSection />
      <SensorsSection />
      <RulesSection />
    </div>
  );
}
