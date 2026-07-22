# Przemyśl Tour 1.5.0 – podręcznik administratora

## 1. Cel wydania

Wersja 1.5.0 zamyka piętnastoetapowy rozwój wtyczki i stanowi stabilne wydanie produkcyjne. Etap 15 nie zmienia modelu wyścigów, tras, uczestników ani wyników. Dodaje końcową diagnostykę, procedury operacyjne, tryb konserwacyjny i dokumentację.

## 2. Pierwsze uruchomienie

1. Wykonaj kopię plików i bazy danych.
2. Zainstaluj aktualizację 1.5.0.
3. Otwórz **Przemyśl Tour → Gotowość produkcyjna**.
4. Kliknij **Uruchom pełny test**.
5. Usuń wszystkie błędy krytyczne.
6. Sprawdź testowy e-mail.
7. Otwórz **Narzędzia → Stan witryny**.
8. Dopiero po zakończeniu testów włącz tryb produkcyjny.

## 3. Znaczenie statusów

- **Poprawne** – test zakończony bez uwag.
- **Zalecenie** – funkcja może działać, ale konfiguracja wymaga poprawy.
- **Krytyczne** – problem może blokować zapisy, mapy, importy, wyniki lub bezpieczeństwo. Nie uruchamiaj produkcji przed jego usunięciem.

## 4. Tryb produkcyjny

Tryb produkcyjny jest deklaracją administratora, że wykonano pełne testy. Po jego włączeniu szczególnie ważne jest wyłączenie publicznego wyświetlania błędów PHP i utrzymanie aktywnego HTTPS.

## 5. Tryb konserwacyjny

Tryb konserwacyjny blokuje publiczne strony wyścigów, tras i poufne widoki wtyczki odpowiedzią HTTP 503. Administrator pozostaje zalogowany i może normalnie pracować. Przed uruchomieniem wydarzenia sprawdź, czy tryb jest wyłączony.

## 6. Raport diagnostyczny

Raport JSON zawiera wersje, wynik testów, status środowiska i zbiorcze liczniki. Nie zawiera imion, nazwisk, e-maili, telefonów, tokenów ani treści zgód uczestników.

## 7. Kopie bezpieczeństwa

Przed każdą aktualizacją wykonuj kopię:

- bazy MySQL/MariaDB,
- katalogu `wp-content/plugins/przemysl-tour-races`,
- katalogu `wp-content/uploads`,
- pliku `wp-config.php`.

Jednorazowy aktualizator Etapu 15 tworzy dodatkowo kopię katalogu wtyczki w `wp-content/uploads/ptr-backups/`.

## 8. Procedura przed wydarzeniem

- sprawdź datę, lokalizację i harmonogram,
- sprawdź każdą trasę oraz plik GPX,
- wykonaj próbny zapis uczestnika,
- wykonaj próbne anulowanie i przepisanie pakietu,
- sprawdź wiadomości e-mail,
- sprawdź limity miejsc,
- przetestuj listę startową,
- wykonaj próbny import wyników,
- sprawdź certyfikat,
- sprawdź mapy na komputerze i telefonie,
- sprawdź klawiaturę, fokus i kontrast,
- pobierz raport gotowości.

## 9. Procedura awaryjna

1. Włącz tryb konserwacyjny.
2. Zapisz godzinę wystąpienia błędu.
3. Pobierz raport diagnostyczny.
4. Sprawdź log PHP i log WordPress.
5. Nie usuwaj tabel uczestników ani wyników.
6. W razie problemu po aktualizacji przywróć katalog wtyczki z kopii oraz bazę danych z tego samego momentu.

## 10. Uprawnienia

Dane osobowe uczestników powinny być dostępne wyłącznie dla administratorów i osób posiadających dedykowane uprawnienia `manage_ptr_registrations` oraz `export_ptr_registrations`. Nie udostępniaj kont administracyjnych współdzielonych przez wiele osób.
