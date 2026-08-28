import type { Sensor } from '@/types/api';

import { formatValue } from './format';

/** Nom d'affichage : el-haress-NN-<nom> fourni par l'API, repli sur le label. */
export function sensorName(sensor: Pick<Sensor, 'display_name' | 'label'>): string {
  return sensor.display_name || sensor.label;
}

/** Un capteur binaire est "Detecte" des que sa valeur depasse 0. */
export function isDetected(value: number | null | undefined): boolean {
  return (value ?? 0) > 0.5;
}

/**
 * Valeur lisible d'un capteur. Binaire -> "Detecte"/"Normal" (via le traducteur
 * fourni) ; continu -> nombre formate suivi de l'unite eventuelle.
 */
export function formatSensorValue(
  sensor: Pick<Sensor, 'is_binary' | 'unit'>,
  value: number | null | undefined,
  locale: string,
  t: (key: string) => string,
): string {
  if (value == null) {
    return '--';
  }
  if (sensor.is_binary) {
    return isDetected(value) ? t('sensor.detected') : t('sensor.normal');
  }
  return `${formatValue(value, locale)}${sensor.unit ? ` ${sensor.unit}` : ''}`;
}
