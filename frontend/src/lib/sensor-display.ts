import type { Sensor } from '@/types/api';

import { formatValue } from './format';

/** Nom d'affichage : el-haress-NN-<nom> fourni par l'API, repli sur le label. */
export function sensorName(sensor: Pick<Sensor, 'display_name' | 'label'>): string {
  return sensor.display_name || sensor.label;
}

/**
 * Valeur d'un capteur : exactement ce que le STE2 renvoie (valeur brute) suivie de
 * son unite. Aucune reinterpretation (pas de forcage en binaire) : un capteur a
 * etats discrets affiche son etat (0, 1, 2, 3...), un capteur continu sa mesure.
 */
export function formatSensorValue(
  sensor: Pick<Sensor, 'unit'>,
  value: number | null | undefined,
  locale: string,
): string {
  if (value == null) {
    return '--';
  }
  return `${formatValue(value, locale)}${sensor.unit ? ` ${sensor.unit}` : ''}`;
}
