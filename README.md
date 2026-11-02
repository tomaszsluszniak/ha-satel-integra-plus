# Satel Integra (extended) dla Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/tomaszsluszniak/ha-satel-integra-plus/actions/workflows/validate.yml/badge.svg)](https://github.com/tomaszsluszniak/ha-satel-integra-plus/actions/workflows/validate.yml)

Rozszerzona wersja wbudowanej integracji **Satel Integra** dla central **Satel INTEGRA** z modułem
**ETHM-1 / ETHM-1 Plus / INT-RS**. Ma tę samą domenę (`satel_integra`), więc zastępuje wbudowaną
integrację **bez ponownej konfiguracji**: istniejący wpis, strefy, wejścia, wyjścia i
identyfikatory encji zostają bez zmian. Dochodzą nowe encje, opcje i akcje.

[![Otwórz repozytorium w HACS w swoim Home Assistant.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tomaszsluszniak&repository=ha-satel-integra-plus&category=integration)
[![Dodaj integrację Satel Integra w swoim Home Assistant.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=satel_integra)

## Co dodaje do wbudowanej integracji

Wbudowana integracja tworzy osobny panel alarmowy dla każdej strefy i ma dwa tryby uzbrajania,
więc uzbrojenie całego domu to kilka osobnych poleceń. Biblioteka `satel-integra`, z której
korzysta, obsługuje tylko część protokołu INT-RS / ETHM-1.

| | wbudowana `satel_integra` (2026.10) | ta integracja |
|---|---|---|
| uzbrojenie / wyłączenie wszystkich stref jednym poleceniem | nie (panel na strefę) | **panel „Wszystkie strefy”** |
| tryby czuwania Satel w interfejsie | poza domem = 0, w domu = jeden ustawiony tryb | **wszystkie cztery**: poza domem = 0 (pełne), niestandardowe = 1 (pełne + blokady), w domu = 2 (bez wewnętrznych), noc = 3 (bez wewnętrznych i bez opóźnień) |
| wynik poleceń czuwania i wyjść | niesprawdzany (sprawdzany od 2026.11) | błędny kod, brak uprawnień, „nie można uzbroić, możliwe wymuszenie”, brak odpowiedzi – zgłaszane jako błąd |
| sabotaż, alarm, pamięć alarmu, blokada, izolacja, maskowanie wejść | nie | czujniki i **przełącznik blokady** dla każdego wejścia |
| strefy z naruszonymi wejściami (gotowość do uzbrojenia), pamięć alarmu | nie | czujniki i atrybuty paneli |
| stan centrali i awarie | nie (dostępne od 2026.11) | tryb serwisowy, awaria systemu, AC, akumulator i pozostałe awarie z części 1 |
| dziennik zdarzeń centrali | nie | **encja zdarzeń** i `satel_integra_event` dla każdego nowego zdarzenia, z treścią i nazwami |
| wymuszone uzbrojenie, blokowanie wejść, przełączanie wielu wyjść, kasowanie pamięci awarii | nie | **akcje** |
| karta Lovelace | nie | **wbudowana karta**, ładowana automatycznie |

## Instalacja (HACS)

1. Otwórz repozytorium w HACS (zostanie przy okazji dodane jako repozytorium własne):

   [![Otwórz repozytorium w HACS w swoim Home Assistant.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tomaszsluszniak&repository=ha-satel-integra-plus&category=integration)

   Albo ręcznie: HACS → ⋮ → **Niestandardowe repozytoria** → `https://github.com/tomaszsluszniak/ha-satel-integra-plus`, typ **Integracja**.
2. **Pobierz** Satel Integra (extended) i zrestartuj Home Assistant.
3. Jeśli używasz już wbudowanej integracji Satel Integra, to wszystko: istniejący wpis działa
   teraz na tej wersji. W przeciwnym razie dodaj integrację:

   [![Dodaj integrację Satel Integra w swoim Home Assistant.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=satel_integra)

   Albo Ustawienia → Urządzenia i usługi → **Dodaj integrację** → **Satel Integra**.

Instalacja ręczna: skopiuj `custom_components/satel_integra` do `/config/custom_components/`
i zrestartuj Home Assistant.

Przy starcie Home Assistant instaluje bibliotekę `satel-integra` 1.6.x. Wymagany Home Assistant
2026.10 lub nowszy.

**Zmiana po przejściu z wbudowanej integracji:** opcja *Wszystkie tryby czuwania Satel w panelach*
jest domyślnie włączona. `alarm_arm_home` uzbraja wtedy zawsze w trybie 2, a nie w trybie ustawionym
dla strefy (domyślnie 1), a strefa czuwająca w trybie 1 lub 3 ma stan `armed_custom_bypass` lub
`armed_night`, a nie `armed_home`. Jeśli automatyzacje na tym polegają, wyłącz tę opcję.

**Powrót do wbudowanej wersji:** usuń integrację w HACS i zrestartuj. Wbudowana integracja
ponownie przejmie ten sam wpis, a encje dodane przez tę wersję zostaną osierocone i można je usunąć.

## Opcje

Ustawienia → Urządzenia i usługi → Satel Integra → **Konfiguruj**:

| Opcja | Domyślnie | |
|---|---|---|
| Kod użytkownika | – | kod do sterowania wyjściami, blokadami wejść i w pozostałych akcjach (oraz w panelach alarmowych i akcjach czuwania, patrz niżej) |
| Używaj zapisanego kodu w panelach alarmowych | wył. | załączanie i wyłączanie czuwania bez wpisywania kodu, w panelach i w akcjach `arm`, `disarm`, `clear_alarm`; każdy z dostępem do Home Assistant może wtedy wyłączyć alarm |
| Wszystkie tryby czuwania Satel w panelach | wł. | poza domem = 0, niestandardowe = 1, w domu = 2, noc = 3; po wyłączeniu: poza domem = 0, w domu = tryb ustawiony dla strefy |
| Panel „Wszystkie strefy” | wł. | jeden panel dla wszystkich stref |
| Strefy sterowane panelem „Wszystkie strefy” | wszystkie | wybrane spośród skonfigurowanych stref |
| Odpytywanie dziennika zdarzeń | 10 s | `0` wyłącza encję zdarzeń i zdarzenia |

Strefy, wejścia i wyjścia konfiguruje się jak dotąd (jako podwpisy integracji).

## Encje

**Panele alarmowe.** Jeden na każdą strefę, jak we wbudowanej integracji, oraz **Wszystkie
strefy**. Stan pokazuje tryb czuwania (`armed_away` = 0, `armed_custom_bypass` = 1,
`armed_home` = 2, `armed_night` = 3) z nazwami trybów Satel. Atrybuty: `arm_mode` (0–3),
`violated_zones`, `alarm_memory`, `first_code_entered`, `temporary_blocked`; w panelu Wszystkie
strefy dodatkowo stan każdej strefy, `armed_partitions`, `disarmed_partitions`,
`partially_armed` i `ready_to_arm`. Panel Wszystkie strefy wysyła jedno polecenie dla wszystkich
stref; gdy strefy czuwają w różnych trybach, pokazuje najsilniejszy.

**Wejścia.** Czujnik wejścia jak dotąd, a do tego *Sabotaż* i *Alarm*, przełącznik *Blokada* oraz
(domyślnie wyłączone) *Pamięć alarmu*, *Alarm sabotażowy*, *Izolacja*, *Maskowanie*,
*Awaria – brak naruszenia* i *Awaria – długie naruszenie*.

**Strefy.** *Naruszone wejścia* (strefa nie jest gotowa do uzbrojenia) i *Pamięć alarmu* oraz
(domyślnie wyłączone) pamięć alarmu pożarowego, blokada czasowa, wprowadzony pierwszy kod, alarm
zweryfikowany i alarm ostrzegawczy.

**Centrala.** *Tryb serwisowy*, *Awaria systemu*, *Awaria zasilania AC*, *Awaria akumulatora* oraz
(domyślnie wyłączone) pozostałe awarie systemowe: wyjścia OUT1–4, zasilanie manipulatorów
i ekspanderów, magistrale DT1 / DT2 / DTM, zegar, monitoring do stacji, EEPROM, RAM, pamięć
restartu. Encja zdarzeń *Dziennik zdarzeń*.

## Karta Lovelace

Integracja dostarcza kartę i sama dodaje ją do zasobów Lovelace, a przy zasobach w trybie YAML
ładuje ją skryptem. Nie trzeba niczego dodawać ręcznie.

```yaml
type: custom:satel-integra-alarm-card
entity: alarm_control_panel.<centrala>_wszystkie_strefy
title: Alarm              # opcjonalnie
show_zones: true
show_outputs: true
show_history: true
confirm_outputs: true     # przełączenie wyjścia wymaga drugiego dotknięcia
exclude: []               # encje do pominięcia
```

Pierścień z segmentem dla każdej strefy w kolorze jej trybu czuwania i stan ogólny; przyciski
czterech trybów czuwania i wyłączenia czuwania, z klawiaturą kodu, gdy panel go wymaga; strefy
z naruszonymi wejściami i pamięcią alarmu; kafelki wejść (naruszenie, sabotaż, alarm, przycisk
blokady); kafelki wyjść; aktywne awarie; ostatnie zdarzenie i dziennik zdarzeń. Strefy, wejścia
i wyjścia są wykrywane automatycznie. Język polski i angielski.

## Akcje

Wszystkie akcje przyjmują opcjonalne `config_entry_id` (potrzebne tylko przy więcej niż jednej
centrali) oraz opcjonalny `code` (domyślnie kod z opcji).

Akcje `arm`, `disarm` i `clear_alarm` używają kodu z opcji tylko wtedy, gdy włączona jest opcja
*Używaj zapisanego kodu w panelach alarmowych*. W przeciwnym razie trzeba podać `code`, tak samo
jak w panelu alarmowym.

| Akcja | Parametry |
|---|---|
| `satel_integra.arm` | `partitions` (domyślnie wszystkie), `mode` 0–3, `force` (wymuszenie), `no_bypass` (bez blokad i bez czasu na wyjście, INT-RS Plus / ETHM-1 Plus 2.19+) |
| `satel_integra.disarm` | `partitions`, `clear_alarm` |
| `satel_integra.clear_alarm` | `partitions` |
| `satel_integra.bypass_zones` | `zones`, `isolate` |
| `satel_integra.unbypass_zones` | `zones` |
| `satel_integra.set_outputs` | `outputs`, `state`: `on` / `off` / `toggle`, wszystkie jednym poleceniem |
| `satel_integra.clear_trouble_memory` | – |
| `satel_integra.read_event_log` | `count` (1–200), zwraca zdarzenia jako odpowiedź |

```yaml
# wymuszone uzbrojenie wybranych stref w trybie 0
action: satel_integra.arm
data:
  partitions: [1, 2, 4]
  mode: 0
  force: true
```

```yaml
# uzbrojenie wszystkich stref w trybie 3 (bez wewnętrznych i bez opóźnień)
action: alarm_control_panel.alarm_arm_night
target:
  entity_id: alarm_control_panel.<centrala>_wszystkie_strefy
```

## Zdarzenia

Dziennik zdarzeń centrali jest odpytywany (protokół nie wysyła go sam). Każdy nowy wpis trafia
na szynę jako `satel_integra_event` oraz do encji *Dziennik zdarzeń*:

```yaml
config_entry_id: 01K...
index: 258
time: "2026-11-01T17:47:00"
class: arming        # zone_alarm, partition_alarm, arming, bypass, access_control, trouble, user_function, system
code: 10
restore: false
text: Wyłączenie czuwania   # treść zdarzenia z centrali, w języku centrali
partition: 1
partition_name: Parter
source: 3
source_name: Jan     # nazwa wejścia lub użytkownika, zależnie od zdarzenia
kind: 2
object: 0
```

Przykład – powiadomienie, kto wyłączył czuwanie:

```yaml
triggers:
  - trigger: event
    event_type: satel_integra_event
    event_data:
      class: arming
actions:
  - action: notify.notify
    data:
      message: >
        {{ trigger.event.data.text }} – {{ trigger.event.data.partition_name }}
        ({{ trigger.event.data.source_name }})
```

## Poprawki biblioteki `satel-integra` 1.6

Nakładane z poziomu integracji (`satel_ext.py`), bez forka biblioteki. Zależą od jej wnętrza,
dlatego manifest dopuszcza tylko serię 1.6.x (`satel-integra>=1.6.0,<1.7`):

- **Połączenia szyfrowane:** biblioteka czytała ramkę przez `StreamReader.read(n)`, które może
  zwrócić mniej bajtów, gdy TCP podzieli ramkę; ucięta ramka nie daje się odszyfrować i połączenie
  jest zrywane. Poprawione (`readexactly`).
- **INT-RS v1.x / ETHM-1 (nie Plus):** biblioteka zawsze wysyła 32-bajtowe maski wejść i wyjść,
  które te moduły po cichu odrzucają. Polecenia dodane tutaj wysyłają 16 bajtów dla numerów do 128;
  z tymi modułami wyjściami steruj akcją `satel_integra.set_outputs`.
- Dodane polecenia: 19 dodatkowych poleceń stanu w monitorowaniu, wymuszone uzbrojenie, uzbrojenie
  bez blokad, blokowanie / odblokowanie / izolacja wejść, wyjścia włącz / wyłącz / przełącz,
  kasowanie pamięci awarii, dziennik zdarzeń z treścią zdarzeń i nazwami urządzeń.

Lista zmian: [CHANGELOG.md](CHANGELOG.md).

## Autorzy i licencja

- Na podstawie integracji Home Assistant `satel_integra` (Apache License 2.0) autorstwa
  @Tommatheussen i współtwórców.
- Korzysta z biblioteki [satel-integra](https://github.com/c-soft/satel_integra) (MIT).
- Protokół: *opis protokołu integracji INT-RS / ETHM-1 Plus*, SATEL 2023-02-22.
- Projekt niezwiązany z SATEL sp. z o.o.

Licencja Apache License 2.0.
