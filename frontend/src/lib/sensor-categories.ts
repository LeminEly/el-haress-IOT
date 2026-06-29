import type { Sensor } from '@/types/api';

export interface SensorCategory {
  id: string;
  labelKey: string;
}

export const CATEGORIES: SensorCategory[] = [
  { id: 'temperature', labelKey: 'category.temperature' },
  { id: 'humidity', labelKey: 'category.humidity' },
  { id: 'gas', labelKey: 'category.gas' },
  { id: 'smoke', labelKey: 'category.smoke' },
  { id: 'motion', labelKey: 'category.motion' },
  { id: 'pressure', labelKey: 'category.pressure' },
  { id: 'light', labelKey: 'category.light' },
  { id: 'sound', labelKey: 'category.sound' },
  { id: 'other', labelKey: 'category.other' },
];

const UNIT_CATEGORY: Record<string, string> = {
  C: 'temperature',
  '°C': 'temperature',
  F: 'temperature',
  '°F': 'temperature',
  K: 'temperature',
  '%': 'humidity',
  RH: 'humidity',
  PPM: 'gas',
  PPB: 'gas',
  LEL: 'gas',
  MG_M3: 'gas',
  PA: 'pressure',
  HPA: 'pressure',
  BAR: 'pressure',
  LUX: 'light',
  DB: 'sound',
  DBA: 'sound',
};

const KIND_MAP: [string, string][] = [
  ['temp', 'temperature'],
  ['temperature', 'temperature'],
  ['thermocouple', 'temperature'],
  ['thermistor', 'temperature'],
  ['humidity', 'humidity'],
  ['humid', 'humidity'],
  ['rh', 'humidity'],
  ['gas', 'gas'],
  ['co2', 'gas'],
  ['co', 'gas'],
  ['ch4', 'gas'],
  ['lpg', 'gas'],
  ['smoke', 'smoke'],
  ['fire', 'smoke'],
  ['flame', 'smoke'],
  ['motion', 'motion'],
  ['movement', 'motion'],
  ['pir', 'motion'],
  ['pressure', 'pressure'],
  ['barometric', 'pressure'],
  ['light', 'light'],
  ['illuminance', 'light'],
  ['sound', 'sound'],
  ['noise', 'sound'],
  ['db', 'sound'],
];

function kindCategory(kind: string): string | undefined {
  const lower = kind.toLowerCase();
  for (const [pattern, cat] of KIND_MAP) {
    if (lower.includes(pattern)) return cat;
  }
  return undefined;
}

export function categorizeSensor(sensor: Sensor): string {
  const unit = sensor.unit?.toUpperCase() ?? '';
  if (UNIT_CATEGORY[unit]) return UNIT_CATEGORY[unit];
  const fromKind = kindCategory(sensor.kind ?? '');
  if (fromKind) return fromKind;
  return 'other';
}

export function groupByCategory(sensors: Sensor[]): Map<string, Sensor[]> {
  const groups = new Map<string, Sensor[]>();
  for (const sensor of sensors) {
    const cat = categorizeSensor(sensor);
    if (!groups.has(cat)) groups.set(cat, []);
    groups.get(cat)!.push(sensor);
  }
  return groups;
}
