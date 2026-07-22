# Changelog – Przemyśl Tour 1.5.0

## Etap 15 – stabilne wydanie produkcyjne

### Dodano

- panel **Przemyśl Tour → Gotowość produkcyjna**,
- automatyczny zestaw testów środowiska, danych, REST API, tabel i bezpieczeństwa,
- zbiorczy wynik gotowości i podział na błędy krytyczne, zalecenia oraz testy poprawne,
- bezpieczny eksport raportu diagnostycznego JSON bez danych osobowych,
- tryb produkcyjny,
- tryb konserwacyjny HTTP 503 ograniczony do stron Przemyśl Tour,
- test poczty systemowej,
- bezpieczne czyszczenie transientów Przemyśl Tour,
- codzienny audyt przez WP-Cron,
- test w WordPress Site Health,
- chroniony endpoint `/wp-json/ptr/v1/system/health`,
- nagłówki `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` i `X-Frame-Options` dla publicznych stron modułu,
- dokumentację administratora,
- checklistę produkcyjną,
- kopię bezpieczeństwa plików podczas instalacji Etapu 15.

### Zmieniono

- wersję kodu z 1.4.0 do 1.5.0,
- wersję danych z 2.2.0 do 2.3.0,
- diagnostykę wtyczki uzupełniono o wynik produkcyjny,
- ustawienia `ptr_settings` uzupełniono bez nadpisywania istniejących wartości.

### Zachowano

- katalog `przemysl-tour-races`,
- główny plik `przemysl-tour-races.php`,
- wszystkie typy treści i adresy URL,
- tabele uczestników i wyników,
- pliki GPX,
- widgety Elementora,
- bloki Gutenberga,
- shortcode,
- ustawienia Google Maps,
- ustawienia SEO i AI,
- dane demonstracyjne.

### Bezpieczeństwo

Aktualizacja nie usuwa ani nie przebudowuje tabel danych. Raporty diagnostyczne używają wyłącznie danych technicznych i liczników zbiorczych.