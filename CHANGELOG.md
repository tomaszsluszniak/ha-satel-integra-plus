# Lista zmian

Nagłówek każdej sekcji to numer wersji bez `v`. Workflow Release pobiera stąd opis wydania dla
tagu `vX.Y.Z`, więc sekcję trzeba dodać przed utworzeniem tagu.

## 2026.11.7

- Karta: integracja rejestruje ją jako zasób Lovelace (w trybie „storage”). Zasoby są wczytywane,
  zanim dashboard utworzy karty, więc karta nie pokazuje już czasem „Błąd konfiguracji”
  w aplikacji mobilnej. Dotąd była dołączana skryptem, na który frontend nie czeka, i na wolniejszym
  urządzeniu dashboard próbował utworzyć kartę, zanim była zdefiniowana. Przy dashboardach
  w trybie YAML działa jak dotąd.
- README: uaktualniony opis ładowania karty.

## 2026.11.6

- **Zmiana zachowania:** akcje `arm`, `disarm` i `clear_alarm` używają kodu z opcji tylko przy
  włączonej opcji *Używaj zapisanego kodu w panelach alarmowych*. Dotąd każdy, kto mógł wywoływać
  akcje w Home Assistant, mógł bez kodu wyłączyć czuwanie, mimo wyłączonej opcji. Automatyzacje
  wywołujące te akcje bez `code` wymagają włączenia opcji lub podania kodu.
- Opisy opcji, pola `code` i komunikat o braku kodu dostosowane do tej zmiany (en, pl).
- Zdarzenia: `partition_name` jest podawane tylko wtedy, gdy zdarzenie faktycznie dotyczy strefy.
  Przy zdarzeniach z numerem manipulatora lub telefonu w tym polu integracja pokazywała nazwę
  przypadkowej strefy.
- Zdarzenia: `satel_integra_event` działa także po wyłączeniu encji *Dziennik zdarzeń*. Dotąd
  odpytywanie dziennika zatrzymywało się razem z nią.
- Manifest: wymaganie `satel-integra>=1.6.0,<1.7` zamiast `==1.6.0`, bo hassfest nie dopuszcza już
  dokładnego przypięcia pakietu, od którego zależy Home Assistant. Integracja łata wnętrze
  biblioteki, dlatego zakres jest ograniczony do serii 1.6.x.
- Manifest: dodana kategoria `security_safety.alarm_systems`.
- Wersja w repozytorium zgodna z tagami (`manifest.json`, karta).
- Usunięty nieużywany plik `www/satel-alarm-card.js`. Integracja od 2026.11.4 ładuje tylko
  `www/satel-integra-alarm-card.js`.
- README: ostrzeżenie o zmianie działania `alarm_arm_home` i stanów paneli po przejściu
  z wbudowanej integracji, porównanie z wersją wbudowaną uaktualnione o 2026.11.
- Usunięty `docs/README.pl.md`, bo główne README jest już po polsku.

## 2026.11.5

- README przepisane na polski.

## 2026.11.4

Pierwsze wydanie.

- Rozszerzona wersja wbudowanej integracji Satel Integra: ta sama domena, a istniejący wpis,
  strefy, wejścia, wyjścia i identyfikatory encji zostają bez zmian; biblioteka satel-integra 1.6.0.
- Panel „Wszystkie strefy”: uzbrajanie i wyłączanie czuwania wszystkich lub wybranych stref jednym
  poleceniem.
- Wszystkie cztery tryby czuwania Satel w panelach: poza domem = 0 (pełne), niestandardowe = 1
  (pełne + blokady), w domu = 2 (bez wewnętrznych), noc = 3 (bez wewnętrznych i bez opóźnień),
  z opcją powrotu do pierwotnego działania.
- Wejścia: sabotaż, alarm, pamięć alarmu, izolacja, maskowanie, awarie braku i długiego naruszenia,
  przełącznik blokady.
- Strefy: naruszone wejścia, pamięć alarmu i inne flagi; stan centrali i awarie.
- Dziennik zdarzeń: encja zdarzeń i `satel_integra_event` dla każdego nowego zdarzenia centrali,
  z treścią oraz nazwami stref, wejść i użytkowników.
- Akcje: uzbrajanie (tryby, wymuszenie, bez blokad), wyłączanie czuwania, kasowanie alarmu,
  blokowanie i odblokowanie wejść, przełączanie wyjść (on / off / toggle), kasowanie pamięci
  awarii, odczyt dziennika zdarzeń.
- Sprawdzanie odpowiedzi centrali: błędny kod, brak uprawnień, „nie można uzbroić, możliwe
  wymuszenie”, brak odpowiedzi.
- Karta Lovelace `custom:satel-integra-alarm-card` udostępniana przez integrację. Poprzednia nazwa
  `custom:satel-alarm-card` nie jest już rejestrowana.
- Poprawki biblioteki: pełny odczyt szyfrowanej ramki podzielonej przez TCP, 16-bajtowe maski wejść
  i wyjść dla INT-RS v1.x / ETHM-1.
