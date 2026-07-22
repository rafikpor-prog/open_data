# Przemyśl Tour – jednorazowy aktualizator Etapu 15

Ten pakiet aktualizuje istniejącą wtyczkę **Przemyśl Tour – Wyścigi i Trasy 1.4.x** do stabilnej wersji **1.5.0**.

Nie jest to nowy moduł funkcjonalny. Po uruchomieniu kopiuje pliki bezpośrednio do istniejącego katalogu `wp-content/plugins/przemysl-tour-races`, aktualizuje główny plik wtyczki i tworzy kopię starego katalogu w `wp-content/uploads/ptr-backups/`.

## Instalacja

1. Wykonaj kopię bazy i plików strony.
2. Wgraj ZIP przez **Wtyczki → Dodaj wtyczkę → Wyślij wtyczkę**.
3. Aktywuj **Przemyśl Tour – Aktualizator Etapu 15**.
4. Otwórz **Narzędzia → Aktualizacja Przemyśl Tour**.
5. Sprawdź kontrolę wstępną.
6. Kliknij **Zainstaluj Etap 15 i zaktualizuj do 1.5.0**.
7. Otwórz **Przemyśl Tour → Gotowość produkcyjna** i uruchom pełny test.
8. Po potwierdzeniu wersji 1.5.0 dezaktywuj i usuń jednorazowy aktualizator.

## Wymagania

- istniejąca wtyczka w katalogu `przemysl-tour-races`,
- wersja głównej wtyczki 1.4.0–1.4.x,
- WordPress 6.0+,
- PHP 7.4+,
- możliwość zapisu w katalogu wtyczki i uploads.

## Ochrona danych

Aktualizator nie usuwa tabel, wpisów ani opcji. Nie modyfikuje rekordów uczestników i wyników. Tworzy kopię całego katalogu wtyczki przed zmianą plików.