# Moteur d'alertes et notifications

El-Haress evalue chaque nouvelle mesure contre les regles de l'entreprise et
notifie sur les canaux configures. **El-Haress est l'unique autorite d'alerte** :
les notifications de la passerelle STE2 restent desactivees (voir
[sensor-system-ste2.md](sensor-system-ste2.md)).

---

## 1. Regle d'alerte (configurable, jamais en dur)

| Champ              | Role                                                       |
| ------------------ | ---------------------------------------------------------- |
| `sensor_id`        | capteur cible, ou `null` pour toute mesure de l'entreprise |
| `condition`        | `GT` \| `GTE` \| `LT` \| `LTE`                              |
| `threshold`        | seuil (propre a chaque entreprise)                         |
| `duration_seconds` | gate anti-pic : seuil franchi pendant N s avant alerte     |
| `cooldown_minutes` | pas de nouveau declenchement avant X min (anti-spam/dedup) |
| `severity`         | `INFO` \| `WARNING` \| `CRITICAL` \| `EMERGENCY`           |
| `channels`         | `whatsapp` \| `sms` \| `email` (un ou plusieurs)           |
| `is_active`        | activation                                                 |

---

## 2. Cycle d'evaluation (a chaque mesure)

```
mesure persistee (collector)
  -> evaluation des regles actives de l'entreprise (capteur cible ou globales)
       -> condition vraie ?
            non  -> reset du suivi de franchissement
            oui  -> cooldown actif ?            -> ignore
                 -> gate de duree satisfaite ?  -> sinon, en attente
                 -> DECLENCHEMENT :
                      - alerte enregistree (alerts, account_id)
                      - cooldown arme (Redis, TTL = cooldown_minutes)
                      - dispatch sur les canaux de la regle
```

- **Gate de duree** : le premier franchissement est horodate dans Redis ; l'alerte
  ne se declenche que si le seuil reste franchi au moins `duration_seconds`.
- **Cooldown / deduplication** : apres declenchement, une cle Redis (TTL =
  `cooldown_minutes`) bloque tout nouveau declenchement de la meme regle/capteur.
- Redis : base logique dediee (deduplication et cooldown des alertes).

---

## 3. Notifications

| Canal      | Provider          | Destinataire (depuis le compte)     |
| ---------- | ----------------- | ----------------------------------- |
| `whatsapp` | Twilio (REST)     | `phone_number`                      |
| `sms`      | Twilio (REST)     | `phone_number`                      |
| `email`    | SMTP (aiosmtplib) | `contact_email` (s'il est renseigne)|

Les secrets (Twilio, SMTP) viennent de la configuration. Un provider non configure
ou un destinataire absent est ignore sans bloquer les autres canaux. Un canal en
echec n'empeche pas les autres.

---

## 4. Cycle de vie des alertes

| Methode | Chemin                  | Description                       |
| ------- | ----------------------- | --------------------------------- |
| GET     | `/alerts`               | historique (filtre `status`)      |
| POST    | `/alerts/{id}/ack`      | acquitter (statut ACKNOWLEDGED)   |

Statuts : `ACTIVE` -> `ACKNOWLEDGED` -> `RESOLVED`. Severites : info, warning,
critical, emergency. Tout est filtre par l'`account_id` du jeton.
