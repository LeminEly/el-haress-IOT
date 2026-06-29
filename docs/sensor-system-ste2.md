# Systeme de capteurs — passerelle HWg STE2 LITE

Reference d'integration de la passerelle physique qui expose les capteurs au
collector El-Haress. Releve sur l'unite reellement deployee. C'est la source de
verite materielle pour la phase Collector (ROADMAP phase 3).

---

## 1. Identite de l'appareil

| Attribut         | Valeur                                  |
| ---------------- | --------------------------------------- |
| Constructeur     | HW group (hw-group.com)                 |
| Modele           | STE2 LITE (Model 102)                    |
| Firmware         | 1.5.1, build 2260 (2023-02-20)          |
| Numero de serie  | 6008200390                              |
| MAC Ethernet     | 00:0A:59:05:F6:A2                       |
| IP (Ethernet)    | 192.168.1.105 / 255.255.255.0           |
| IP (WiFi, STA)   | 192.168.1.91 (interface WiFi desactivee)|
| Nom appareil     | STE2 LITE 5905-F6A2                      |

> L'appareil est une passerelle Ethernet/WiFi a sondes 1-Wire. Il **ne stocke
> aucun historique** (aucun endpoint d'historique) : il n'expose que l'instant
> courant. L'historisation est la responsabilite d'El-Haress (TimescaleDB).

---

## 2. Protocole — HTTP / XML

L'appareil expose plusieurs endpoints HTTP. Le seul a utiliser par le collector
est **`GET /values.xml`** : format machine stable, versionne, dedie a la lecture.

| Endpoint            | Usage                                          | A utiliser ?      |
| ------------------- | ---------------------------------------------- | ----------------- |
| `GET /values.xml`   | Valeurs capteurs, format machine (XmlVer 1.01) | **Oui (collector)** |
| `GET /`             | Config + UI (XmlVer 2.00), inclut SafeRange    | Reference seulement|
| `GET /status.xml`   | Etat pour l'UI web (libelles localises)        | Non (UI)          |
| `GET /sensor.xml`   | Page de configuration des capteurs             | Non (UI)          |
| autres `*.xml`      | Pages de configuration (email, sms, snmp...)   | Non               |

Caracteristiques HTTP observees : `Content-Type: text/xml`,
`Cache-Control: no-store` (chaque appel renvoie l'instant courant). Aucune
sortie JSON disponible (`?fmt=json` renvoie quand meme du XML).

---

## 3. Structure de `values.xml`

Namespace : `http://www.hw-group.com/XMLSchema/ste/values.xsd`.

```xml
<val:Root>
  <Agent>
    <Version>1.5.1</Version> <XmlVer>1.01</XmlVer>
    <DeviceName>STE2 LITE 5905-F6A2</DeviceName>
    <MAC>00:0A:59:05:F6:A2</MAC> <IP>192.168.1.105</IP>
    <UpTime>12138</UpTime>
  </Agent>
  <SenSet>
    <Entry>
      <ID>16145</ID>
      <Name>Sensor 16145</Name>
      <Units>C</Units>
      <Value>30.5</Value>
      <Min>10.0</Min> <Max>60.0</Max> <Hyst>1.0</Hyst>
      <State>1</State>
      <status><state>1</state><alarm>0</alarm></status>
      <Exp>-1</Exp>
    </Entry>
    ...
  </SenSet>
</val:Root>
```

### Champs d'une `<Entry>`

| Champ              | Sens                                                            |
| ------------------ | -------------------------------------------------------------- |
| `ID`               | Identifiant du point de mesure sur la passerelle (entier)       |
| `Name`             | Libelle configure sur l'appareil                                |
| `Units`            | Unite physique : `C` (Celsius), vide si capteur invalide        |
| `Value`            | Valeur courante. **`-999.9` = capteur absent / invalide**       |
| `Min` / `Max`      | Plage de securite configuree **sur l'appareil** (informative)   |
| `Hyst`             | Hysteresis configuree sur l'appareil                            |
| `State`            | `1` = lecture valide, `0` = invalide / non connecte             |
| `status/state`     | Idem `State`                                                    |
| `status/alarm`     | `1` si l'appareil considere le capteur en alarme, sinon `0`     |
| `Exp`              | Exposant decimal applique par l'appareil (deja applique a Value)|
| `Resistance`       | Present pour les detecteurs de type contact / flood             |

---

## 4. Capteurs actuellement declares (3)

Releve sur l'unite. Le `SenId` (adresse materielle 1-Wire) provient de la config
appareil (`GET /`) et est l'identifiant **physiquement stable** ; le `ID` est le
binding sur la passerelle.

| ID    | SenId (1-Wire)     | Nom          | Type     | Unite | Etat releve        | Plage appareil |
| ----- | ------------------ | ------------ | -------- | ----- | ------------------ | -------------- |
| 16145 | 28113fe50e0000a5   | Sensor 16145 | Temp.    | C     | 30.5 C — **Normal**| 10.0 – 60.0    |
| 6686  | 281e1a6704c80aa3   | Sensor 6686  | Temp.    | C     | -999.9 — Invalide  | 10.0 – 35.0    |
| 12571 | 261b318f0c0c09a2   | Flood        | Flood    | —     | -999.9 — Invalide  | n/a            |

Observations :

- Un seul capteur fournit une mesure reelle au moment du releve (16145, 30.5 C).
  Les deux autres sont declares mais non connectes (`-999.9`).
- `Flood` (12571) est un detecteur d'inondation (contact), pas une mesure
  continue : champ `Resistance`, unite vide.
- Les codes d'unite de la config appareil observes : `1` -> temperature Celsius,
  `5` -> detecteur de type flood. **Ne pas s'y fier en dur** : le champ `Units`
  de `values.xml` (`C` ou vide) est la source pour l'unite affichee.

---

## 5. Regles de parsing — a respecter dans le collector

1. **Source unique** : interroger `GET /values.xml`, jamais les pages UI.
2. **Identite stable** : referencer un capteur par son `SenId` (1-Wire) cote
   El-Haress, pas par le `ID` de passerelle qui peut changer au re-binding. Le
   `SenId` se lit dans `GET /` (config), a apparier une fois avec le `ID`.
3. **Sentinelle d'invalidite** : `Value == -999.9` **ou** `State == 0` **ou**
   `Units` vide => lecture invalide. Ne pas inserer de mesure ; marquer le
   capteur `offline`. Ne jamais traiter `-999.9` comme une temperature reelle.
4. **Decouverte dynamique** : la liste des capteurs vient de `<SenSet>`, jamais
   d'une liste codee en dur (regle de genericite El-Haress). Un capteur ajoute
   sur la passerelle doit apparaitre sans modification de code.
5. **Seuils** : `Min`/`Max`/`Hyst` de l'appareil sont **informatifs**. La verite
   des seuils est dans `alert_rules` (notre base). On peut les importer comme
   valeurs initiales lors de la declaration d'un capteur, jamais les lire en
   continu pour declencher une alerte.
6. **Horodatage** : l'appareil ne date pas la mesure. Le collector horodate a la
   reception (`recorded_at = now()` cote serveur, UTC).
7. **Robustesse** : timeout court (l'appareil repond en < 1 s), retry avec
   backoff, et detection de capteur muet (pas de lecture valide depuis N cycles).

---

## 6. Correspondance vers le modele de donnees El-Haress

```
values.xml <Entry>            ->  table  sensors / readings
------------------------------    --------------------------------------------
SenId (1-Wire)                ->  sensors.hardware_id   (cle stable, unique)
ID (passerelle)               ->  sensors.gateway_ref   (informative)
Name                          ->  sensors.label         (valeur initiale, editable)
Units                         ->  sensors.unit          ("C", ...)
type (Temp./Flood/...)        ->  sensors.kind
Value (si valide)             ->  readings.value
recorded_at = now() UTC       ->  readings.recorded_at  (cle d'hypertable)
State / status                ->  statut runtime (normal / offline)
account_id (du contexte)      ->  sensors.account_id / readings.account_id (NOT NULL)
```

L'`account_id` n'existe pas sur l'appareil : il est attribue cote El-Haress lors
de la declaration du capteur (rattachement passerelle -> entreprise). Une
passerelle STE2 appartient a une entreprise ; tous ses capteurs heritent de cet
`account_id`. Le mapping passerelle -> `account_id` est une donnee de
configuration, jamais codee en dur.

---

## 7. Posture de securite — points releves

- **`values.xml` est accessible sans authentification** sur le LAN (HTTP 200 sans
  identifiants). A traiter comme une source non fiable et non chiffree :
  - le collector doit valider/borner chaque valeur recue (pas de confiance
    aveugle dans `Value`) ;
  - l'appareil reste sur un segment reseau interne, jamais expose directement ;
    l'acces externe passe exclusivement par El-Haress (Cloudflare Tunnel).
- Le STE2 propose une page `Security` (`security.xml`). Recommandation : activer
  l'authentification de l'appareil en production et fournir d'eventuels
  identifiants au collector via variables d'environnement (jamais en dur).
- L'horloge de l'appareil est a `1970-01-01` (SNTP non configure) : ne jamais
  utiliser la date de l'appareil ; l'horodatage fait foi cote serveur.

---

## 8. Configuration collector associee

Variables `.env` concernees (voir `.env.example`) :

```
STE2_BASE_URL=http://192.168.1.105
COLLECTOR_POLL_INTERVAL_SECONDS=10
```

`STE2_BASE_URL` et l'intervalle de polling sont **configurables**, jamais en dur.
Une evolution multi-passerelles (plusieurs STE2) se modelise par une table de
passerelles rattachees a un `account_id`, pas par des constantes.

---

## 9. Cartographie complete de l'appareil

Toutes les pages de configuration ont ete explorees. Synthese de l'etat reel
releve, pour qu'aucune capacite cachee ne provoque de conflit avec El-Haress.

| Domaine        | Etat releve sur l'unite                                  | Actif ? |
| -------------- | ------------------------------------------------------- | ------- |
| Reseau         | Ethernet, IP 192.168.1.105 — passer en **statique** (sec. 11) | oui |
| WiFi           | `wifi_enable=0` — desactive (Ethernet uniquement)        | non     |
| IPv6           | desactive (eth et wifi)                                  | non     |
| HTTP           | port 80, **sans authentification** (user/pass vides)     | oui     |
| HTTPS          | port 443 disponible, serveur https non force             | partiel |
| Capteurs       | 3 declares (`enabled=1`), 1 seul connecte (16145)        | oui     |
| Sorties relais | `<outputs>` vide — le modele LITE n'a pas de relais      | non     |
| Email (SMTP)   | valeurs **placeholder** (`some.smtp.server`), `auth=0`   | non     |
| SMS            | `enable=0` (passerelle SMS HTTP externe non configuree)  | non     |
| Portal HWg     | `PushEnable=0`, `AutoPush=0` (serveur hwg-cloud.com)     | non     |
| SNMP           | port 161, communautes `public`(r)/`private`(rw), v3 on   | **oui** |
| Syslog         | `enable=0`                                               | non     |
| SNTP (heure)   | serveur `europe.pool.ntp.org`, **non synchronise (1970)**| non     |
| Upgrade FW     | serveur HTTP `www.hw-group.com` (non chiffre)            | manuel  |
| Reminders      | `alarmReminderPeriod=0`                                  | non     |

---

## 10. Canaux d'alerte de l'appareil — eviter le double-declenchement

L'appareil sait, en theorie, notifier seul (email, SMS, trap SNMP, push portal).
**Aujourd'hui aucun de ces canaux n'est fonctionnel** :

- SMTP : configuration factice, pas de vrai serveur ni destinataire.
- SMS : desactive.
- Portal : push desactive.
- `AlarmMsgRecipID=0` sur **les trois** capteurs : meme si un seuil est franchi,
  l'appareil n'a aucun destinataire a qui envoyer une alarme.

**Regle pour El-Haress : El-Haress est l'unique autorite d'alerte.** Le STE2 reste
une source de mesure passive, en lecture seule. Pour eviter tout conflit futur
(double notification, divergence de seuils) :

1. **Ne jamais activer** les notifications cote appareil (email / SMS / portal /
   traps). Les laisser desactivees et `AlarmMsgRecipID=0`.
2. Les seuils de l'appareil (`SafeRangeLow/Hi`) ne servent qu'a titre indicatif.
   La verite des seuils vit dans `alert_rules` (notre base). Ne jamais
   synchroniser l'un vers l'autre automatiquement.
3. Le collector fait **uniquement** `GET /values.xml`. Il n'ecrit jamais la
   configuration de l'appareil (pas de POST de formulaire, pas de write SNMP).

---

## 11. Stabilite d'adressage et resilience — risque de conflit principal

### Topologie reelle — liaison directe PC <-> STE2

Au stade developpement, le STE2 n'est pas derriere un routeur : il est relie en
**direct par cable RJ45 a la machine de developpement** (liaison point-a-point).
La machine fournit l'adressage du segment `192.168.1.0/24`. Auparavant, un serveur
DHCP temporaire (`dnsmasq` sur la machine) attribuait `.105` au STE2 par sa MAC,
ce qui imposait de relancer dnsmasq a chaque session et cassait la connexion au
moindre debranchement (l'IP de l'interface hote disparaissait).

### Etat final retenu et applique

| Element                | Configuration                                   | Effet                              |
| ---------------------- | ----------------------------------------------- | ---------------------------------- |
| STE2 (appareil)        | **IP statique** 192.168.1.105 / 255.255.255.0, GW 192.168.1.1, DNS 192.168.1.1 (DHCP decoche) | Garde son IP seul, sans DHCP |
| Interface hote `eth0`  | Profil NetworkManager persistant `ste2-link`, IPv4 **manuel** 192.168.1.1/24, autoconnect | Reprend son IP a chaque branchement / reboot |
| Profil concurrent      | `Wired connection 1` (DHCP) en priorite inferieure | Ne prend pas la main sur `ste2-link` |
| dnsmasq                | **Retire**                                      | Plus aucune etape manuelle         |

Resultat : `ping 192.168.1.105` repond des le branchement du cable, sans aucune
commande. Recommande pour lever toute ambiguite : forcer
`ste2-link` en priorite autoconnect superieure
(`nmcli connection modify ste2-link connection.autoconnect-priority 100`).

> En production (sur Raspberry Pi plutot que sur le PC de dev), le meme principe
> s'applique : STE2 en IP statique sur le segment capteurs, interface du Pi en IP
> statique sur ce segment. Aucun DHCP necessaire.

Defense en profondeur cote collector (independante de l'adressage) : ne pas
dependre d'une IP figee en dur. `STE2_BASE_URL` est une configuration ; en cas de
changement, le collector peut resoudre l'appareil par nom d'hote
(`STE2LITE5905-F6A2`) ou le redecouvrir par MAC sur le segment. Un changement
d'adresse degrade le service sans le casser.

Autres points de resilience cote collector :

- Horloge appareil a `1970` : **toujours** horodater cote serveur (UTC). Ne jamais
  lire `Time`/`Date` de l'appareil.
- L'appareil rafraichit ses mesures en interne (`www_update_period=1s`) ; notre
  intervalle de polling est independant et configurable.
- Detecter le capteur muet : plusieurs cycles consecutifs a `-999.9`/`State=0`
  => statut `offline`, sans polluer l'historique de valeurs sentinelles.

---

## 12. Durcissement de l'appareil — recommandations de production

Releve d'audit sur l'unite (a corriger avant mise en production reelle) :

| Risque releve                                          | Action recommandee                                   |
| ------------------------------------------------------ | ---------------------------------------------------- |
| Interface web **sans mot de passe** (HTTP ouvert)      | Definir un identifiant web ; restreindre au LAN      |
| SNMP communautes par defaut `public`/`private` (write) | Desactiver SNMP (inutile a El-Haress) ou v3 + ACL    |
| `private` en lecture/ecriture                          | Couper l'ecriture SNMP                                |
| HTTP en clair                                          | Activer HTTPS (port 443) si le collector le supporte |
| DHCP (IP mouvante)                                     | Reservation DHCP / IP statique (voir section 11)     |
| Appareil joignable au-dela du segment capteurs         | VLAN / segment dedie ; jamais expose a l'exterieur   |

L'appareil ne doit jamais etre accessible depuis Internet. L'acces externe au
systeme passe exclusivement par El-Haress (Cloudflare Tunnel). Le STE2 vit sur un
segment interne, en lecture seule pour le collector.

---

## 13. Recapitulatif — contrat d'integration

- Source de donnees unique : `GET http://<ste2>/values.xml` (lecture seule).
- Identite capteur stable : `SenId` (1-Wire), apparie une fois avec le `ID`.
- Valeur invalide : `-999.9` / `State=0` / `Units` vide => `offline`, pas d'insert.
- Horodatage : serveur, UTC ; jamais l'horloge appareil.
- Decouverte dynamique des capteurs ; aucun capteur ni seuil code en dur.
- Seuils : `alert_rules` (notre base) font foi ; ceux de l'appareil sont ignores.
- Alerte : El-Haress uniquement ; notifications appareil laissees desactivees.
- Adressage : reservation DHCP / IP statique pour figer `STE2_BASE_URL`.
