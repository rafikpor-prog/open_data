# Checklista weryfikacji produkcyjnej Przemyśl Tour 1.5.0

## A. Środowisko

- [ ] WordPress 6.0 lub nowszy.
- [ ] PHP 8.1 lub nowszy; minimum 7.4.
- [ ] HTTPS działa na wszystkich stronach.
- [ ] Przyjazne odnośniki są włączone.
- [ ] Limit pamięci PHP wynosi co najmniej 256M.
- [ ] Katalog uploads jest zapisywalny.
- [ ] SimpleXML, JSON i Mbstring są aktywne.
- [ ] WP-Cron lub cron systemowy działa.
- [ ] Publiczne wyświetlanie błędów jest wyłączone.

## B. Dane i tabele

- [ ] Tabela uczestników istnieje.
- [ ] Tabela wyników istnieje.
- [ ] Typy treści wyścigów i tras są dostępne.
- [ ] Wyścigi i trasy zachowały adresy URL po aktualizacji.
- [ ] Liczby zgłoszeń zgadzają się ze stanem przed aktualizacją.
- [ ] Liczby wyników zgadzają się ze stanem przed aktualizacją.

## C. Wyścigi i trasy

- [ ] Hero i opis wyścigu działają.
- [ ] Harmonogram jest czytelny.
- [ ] Wszystkie trasy są przypisane do właściwego wydarzenia.
- [ ] Mapa ładuje się po przewinięciu.
- [ ] Profil wysokościowy jest zgodny z GPX.
- [ ] Pobieranie GPX działa.
- [ ] Segmenty i punkty organizacyjne są kompletne.
- [ ] Widok mobilny nie powoduje przewijania poziomego strony.

## D. Zapisy

- [ ] Formularz zapisów działa dla każdej trasy.
- [ ] Obowiązkowe zgody blokują wysłanie bez akceptacji.
- [ ] Limit wydarzenia działa.
- [ ] Limit trasy działa.
- [ ] Lista rezerwowa działa.
- [ ] Wiadomość dla zawodnika dociera.
- [ ] Wiadomość organizatora dociera.
- [ ] Poufny link zarządzania działa.
- [ ] Anulowanie działa.
- [ ] Przepisanie pakietu wymaga nowych danych i zgód.

## E. Wyniki

- [ ] Import próbnego CSV działa.
- [ ] Import próbnego XLSX działa.
- [ ] FINISHED, DNS, DNF i DSQ są prezentowane prawidłowo.
- [ ] Remisy mają właściwe miejsca.
- [ ] Kategorie i klasyfikacje K/M/Open są poprawne.
- [ ] Klasyfikacja drużynowa jest poprawna.
- [ ] Publiczna wyszukiwarka nie ujawnia danych prywatnych.
- [ ] Certyfikat finiszera działa.

## F. WCAG i mobile

- [ ] Wszystkie funkcje są dostępne klawiaturą.
- [ ] Fokus jest widoczny.
- [ ] Kontrast spełnia WCAG 2.1 AA.
- [ ] Tabele zmieniają się w karty na telefonie.
- [ ] Komunikaty są przekazywane przez aria-live.
- [ ] prefers-reduced-motion jest respektowane.
- [ ] Mapa ma nazwę dostępną i alternatywę tekstową.

## G. SEO i bezpieczeństwo

- [ ] Canonical jest poprawny.
- [ ] Schema.org nie jest zduplikowane.
- [ ] Open Graph ma obraz i opis.
- [ ] Mapy XML zwracają HTTP 200.
- [ ] Strony zarządzania i certyfikaty mają noindex.
- [ ] Klucz Google Maps jest ograniczony do domeny i Maps JavaScript API.
- [ ] Administratorzy mają włączone silne hasła i 2FA.
- [ ] Raport diagnostyczny nie zawiera danych osobowych.

## H. Decyzja wdrożeniowa

- [ ] Brak błędów krytycznych w panelu Gotowość produkcyjna.
- [ ] Wynik gotowości został zaakceptowany przez administratora.
- [ ] Dostępna jest aktualna kopia plików i bazy.
- [ ] Wyznaczono osobę odpowiedzialną za monitoring po wdrożeniu.
- [ ] Tryb konserwacyjny został wyłączony.
