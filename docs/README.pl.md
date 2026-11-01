# Satel Integra (extended) – opis po polsku

English: [README](../README.md), zmiany: [CHANGELOG](../CHANGELOG.md)

Rozszerzona wersja wbudowanej integracji **Satel Integra** (centrale INTEGRA z modułem
ETHM-1 / ETHM-1 Plus / INT-RS). Ma tę samą domenę (`satel_integra`), więc **zastępuje
wbudowaną integrację bez ponownej konfiguracji**: istniejący wpis, strefy, wejścia, wyjścia
i identyfikatory encji zostają bez zmian. Dochodzą nowe encje i akcje.

Bazuje na kodzie integracji z Home Assistant 2026.10 i bibliotece
[`satel-integra`](https://github.com/c-soft/satel_integra) 1.6.0, uzupełnionej o brakujące
polecenia protokołu (opis protokołu INT-RS / ETHM-1 Plus, SATEL 2023-02-22).

## Co dodaje

| Funkcja | Opis |
| --- | --- |
| **Wszystkie tryby czuwania** | Każdy panel (strefy i „Wszystkie strefy”) ma cztery przyciski uzbrajania odpowiadające trybom Satel: **poza domem = 0 czuwanie pełne**, **niestandardowe = 1 pełne + blokady**, **w domu = 2 bez wewnętrznych**, **noc = 3 bez wewnętrznych i bez opóźnień**. Stan panelu pokazuje tryb, w jakim strefa czuwa (atrybut `arm_mode` 0–3). Opcję można wyłączyć – wtedy jak w oryginale: poza domem = 0, w domu = tryb ustawiony dla strefy. |
| **Panel „Wszystkie strefy”** | Jeden `alarm_control_panel`, który uzbraja i rozbraja wszystkie (lub wybrane) strefy **jednym poleceniem do centrali**, tak jak manipulator, w wybranym trybie 0–3. Stan: tryb czuwania (przy różnych trybach – najsilniejszy); gdy czuwa tylko część stref, atrybut `partially_armed` = `true`. Atrybuty: stan każdej strefy, `armed_partitions`, `disarmed_partitions`, `ready_to_arm`. |
| **Wejścia** | Dla każdego wejścia: *Sabotaż*, *Alarm* oraz (domyślnie wyłączone) *Pamięć alarmu*, *Alarm sabotażowy*, *Izolacja*, *Maskowanie*, *Awaria – brak/długie naruszenie*. Przełącznik **Blokada** (blokowanie/odblokowanie wejścia). |
| **Strefy** | *Naruszone wejścia* (strefa nie jest gotowa do uzbrojenia), *Pamięć alarmu* oraz (domyślnie wyłączone) pamięć alarmu pożarowego, blokada czasowa, pierwszy kod, alarm zweryfikowany/ostrzegawczy. Te same informacje są atrybutami paneli. |
| **Centrala** | Tryb serwisowy, awaria systemu, awaria AC, awaria akumulatora oraz (domyślnie wyłączone) pozostałe awarie z części 1 (wyjścia OUT1–4, zasilania, magistrale, monitoring, RTC, RAM…). |
| **Dziennik zdarzeń** | Encja `event` „Dziennik zdarzeń” i zdarzenie `satel_integra_event` na szynie HA dla **każdego nowego wpisu w pamięci zdarzeń centrali** (z treścią zdarzenia, nazwą strefy, wejścia lub użytkownika). Pozwala np. sprawdzić, kto i z którego manipulatora rozbroił alarm. |
| **Akcje** | `satel_integra.arm` (lista stref, tryb 0–3, **wymuszenie**, bez blokad i czasu na wyjście), `disarm`, `clear_alarm`, `bypass_zones` (także izolacja), `unbypass_zones`, `set_outputs` (on/off/**toggle**, wiele wyjść w jednej ramce), `clear_trouble_memory`, `read_event_log` (zwraca listę zdarzeń). |
| **Komunikaty błędów** | Odpowiedź centrali jest sprawdzana: zły kod, brak uprawnień, „nie można uzbroić, możliwe wymuszenie”, brak połączenia, brak odpowiedzi. Dotąd polecenie mogło przepaść bez śladu. |
| **Kod w opcjach** | Opcjonalnie panele mogą używać kodu zapisanego w opcjach (bez klawiatury w UI). Domyślnie wyłączone; uwaga: każdy z dostępem do HA może wtedy rozbroić alarm. |

## Karta „Satel Integra – alarm”

Integracja sama udostępnia kartę Lovelace (bez osobnej instalacji przez HACS). Po restarcie
HA wybierz ją w edytorze dashboardu albo wklej:

```yaml
type: custom:satel-integra-alarm-card
entity: alarm_control_panel.<centrala>_wszystkie_strefy
```

Karta pokazuje stan wszystkich stref na pierścieniu (jeden segment na strefę, kolor = tryb
czuwania), przyciski trybów 0–3 i wyłączenia czuwania (z klawiaturą kodu, jeśli panel go
wymaga), listę stref z naruszonymi wejściami i pamięcią alarmu, kafelki wejść (naruszenie,
sabotaż, alarm, przycisk blokady), wyjścia (przełączanie z potwierdzeniem drugim dotknięciem),
aktywne awarie oraz dziennik zdarzeń. Strefy, wejścia i wyjścia są wykrywane automatycznie.

Opcje: `title`, `show_zones`, `show_outputs`, `show_history`, `confirm_outputs` (domyślnie
`true`), `exclude` (lista encji do pominięcia).

## Instalacja (HACS)

[![Otwórz w HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tomaszsluszniak&repository=ha-satel-integra-plus&category=integration)
[![Dodaj integrację](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=satel_integra)

1. Kliknij przycisk powyżej (otworzy to repozytorium w HACS w Twoim Home Assistant)
   albo ręcznie: HACS → menu ⋮ → *Custom repositories* → adres tego repozytorium,
   typ **Integration**.
2. Zainstaluj „Satel Integra (extended)” i **zrestartuj Home Assistant**.
3. Gotowe. Istniejący wpis Satel Integra zacznie używać tej wersji. Przy starcie HA
   zainstaluje bibliotekę `satel-integra==1.6.0`.
4. Opcje integracji (*Ustawienia → Urządzenia i usługi → Satel Integra → Konfiguruj*):
   kod, wszystkie tryby czuwania na przyciskach paneli (domyślnie włączone), panel „Wszystkie strefy” i wybór jego stref, użycie kodu w panelach, częstotliwość
   odpytywania dziennika zdarzeń (domyślnie 10 s, 0 wyłącza).

Odinstalowanie: usuń w HACS i zrestartuj. Wraca wbudowana integracja; nowe encje
(panel „Wszystkie strefy”, sabotaże itd.) staną się osierocone i można je usunąć.

## Przykłady

Uzbrojenie wszystkich stref w trybie 3 (bez wewnętrznych i bez opóźnień) jedną akcją
(zamiast kilku paneli z opóźnieniami):

```yaml
action: alarm_control_panel.alarm_arm_night
target:
  entity_id: alarm_control_panel.<centrala>_wszystkie_strefy
```

Wymuszone uzbrojenie wybranych stref w trybie 0 (np. gdy otwarte okno blokuje uzbrojenie):

```yaml
action: satel_integra.arm
data:
  partitions: [1, 2, 4]
  mode: 0
  force: true
```

Powiadomienie, kto rozbroił alarm:

```yaml
triggers:
  - trigger: event
    event_type: satel_integra_event
    event_data:
      class: arming
conditions:
  - condition: template
    value_template: "{{ 'wyłącz' in (trigger.event.data.text or '') | lower }}"
actions:
  - action: notify.notify
    data:
      message: >
        {{ trigger.event.data.text }} – {{ trigger.event.data.partition_name }}
        ({{ trigger.event.data.source_name }})
```

Ostatnie 20 zdarzeń (Narzędzia deweloperskie → Akcje, „zwróć odpowiedź”):

```yaml
action: satel_integra.read_event_log
data:
  count: 20
```

Pola zdarzenia: `index`, `time`, `class` (`zone_alarm`, `partition_alarm`, `arming`,
`bypass`, `access_control`, `trouble`, `user_function`, `system`), `code`, `restore`,
`text`, `partition`, `partition_name`, `source`, `source_name`, `kind`, `object`.

## Przegląd biblioteki `satel-integra` 1.6.0

Poprawki są nakładane z poziomu integracji (`satel_ext.py`), bez forka biblioteki.
Dlatego wersja biblioteki jest przypięta (`==1.6.0`).

Błędy:

1. **Szyfrowanie: niepełny odczyt ramki.** `SatelEncryptedTransport` czytał PDU przez
   `StreamReader.read(n)`, które może zwrócić mniej niż `n` bajtów, gdy TCP podzieli ramkę.
   Ucięta ramka nie daje się odszyfrować i połączenie jest zrywane (sporadyczne rozłączenia
   przy włączonym szyfrowaniu). Potwierdzone testem; **poprawione** (`readexactly`).
2. **Wyjścia zawsze z 32-bajtową maską.** Według protokołu INT-RS v1.x / ETHM-1 (nie Plus)
   przyjmują tylko 16 bajtów, a ramkę o złej długości moduł po cichu odrzuca. Polecenia
   dodane tutaj (`set_outputs`, blokady) wysyłają 16 bajtów, gdy numery są ≤ 128.
   Przełączniki wyjść nadal korzystają z biblioteki: z ETHM-1 Plus działają, ze starym ETHM-1
   lepiej używać `satel_integra.set_outputs`.
3. **Nazwy dekodowane jako latin-1.** Polskie znaki w nazwach z centrali są przekłamane.
   W dzienniku zdarzeń nazwy są dekodowane jako cp1250.
4. **Brak kodu → `TypeError`.** `arm()` / `disarm()` z `code=None` kończą się `len(None)`
   zamiast czytelnego błędu (w 1.5.0 ramka szła bez kodu i centrala ją ignorowała).
   Integracja sprawdza kod wcześniej.

Ograniczenia, które ta wersja uzupełnia: biblioteka obsługuje 14 z ok. 50 poleceń stanu
(brak sabotaży, blokad, pamięci alarmów, stref z naruszonymi wejściami…), nie ma wymuszonego
uzbrajania, blokowania wejść, przełączania (toggle) wyjść, kasowania pamięci awarii ani
odczytu dziennika zdarzeń.

Uwagi do wbudowanej integracji HA 2026.10:

- Brak sterowania wieloma strefami naraz: każda strefa to osobny panel i osobna ramka.
- Używa przestarzałego `register_callbacks`, przez co aktualizacja stref jest planowana po
  **każdej** odebranej ramce (także keepalive).
- Polecenia nie czekają na wynik, więc błędny kod albo odmowa uzbrojenia nie dają żadnego
  komunikatu.

## Rozwój

- `custom_components/satel_integra/satel_ext.py` – rozszerzenie biblioteki (nowe polecenia,
  poprawki).
- `tests/test_satel_ext.py`, `tests/test_ha_layer.py` – testy na symulatorze ETHM-1 Plus z
  repozytorium biblioteki (`tools/ethm_simulator`), warstwa HA na uproszczonych zaślepkach:
  `PYTHONPATH=<satel_integra>:<satel_integra>/tools/ethm_simulator python tests/test_ha_layer.py`
- `script/strings.json` → `translations/en.json` + `pl.json`:
  `python script/build_translations.py <ha-core>/homeassistant/strings.json`

Kod integracji pochodzi z Home Assistant (Apache-2.0) i jest rozwijany na tej samej licencji.

## Wydania

Wydanie tworzy workflow `Release` po wypchnięciu tagu. Ustawia wersję w `manifest.json` i w
karcie, buduje `satel_integra.zip` (to instaluje HACS) i bierze opis zmian z `CHANGELOG.md`:

```bash
git tag v1.0.0 && git push origin v1.0.0
```

Istniejący tag można zbudować ponownie ręcznie (*Actions → Release → Run workflow*).
Workflow `Validate` uruchamia walidację HACS i hassfest.
