# RadioDrive 1.0

Nowoczesna aplikacja radia internetowego dla telefonu/tabletu z obsługą Android Auto.

## Co działa w szkielecie 1.0

- natywny interfejs Jetpack Compose (Material 3)
- streaming MP3/AAC/HLS przez Jetpack Media3 / ExoPlayer
- odtwarzanie w tle przez `MediaLibraryService`
- Android Auto (`media`)
- katalog: Ulubione / Ostatnio słuchane / Wszystkie / Kategorie
- wyszukiwanie po nazwie, opisie i kategorii na poziomie biblioteki Media3
- ulubione i historia zapisane lokalnie
- obsługa zewnętrznych kontrolek MediaSession (Bluetooth, kierownica, ekran blokady)
- przykładowe stacje w `app/src/main/assets/stations.json`

## Uruchomienie

1. Otwórz katalog `RadioDrive` w aktualnym Android Studio.
2. Użyj JDK 17.
3. Poczekaj na Gradle Sync.
4. Uruchom moduł `app` na telefonie z Androidem 8.0+.
5. Android Auto testuj przez telefon + samochód lub Desktop Head Unit (DHU).

## Własne stacje

Edytuj:

`app/src/main/assets/stations.json`

Każdy rekord:

```json
{
  "id": "unikalne-id",
  "name": "Nazwa stacji",
  "subtitle": "opis",
  "streamUrl": "https://...",
  "category": "Polskie",
  "logoUrl": "https://.../logo.png"
}
```

W kolejnej wersji plik lokalny powinien zostać zastąpiony Twoim REST API z istniejącego backendu IPTV. Model danych został celowo wydzielony, żeby nie przepisywać warstwy odtwarzania i Android Auto.

## Android Auto

Aplikacja deklaruje `com.google.android.gms.car.application` i `automotive_app_desc.xml` z `uses name="media"`. `RadioPlaybackService` jest `MediaLibraryService`, dzięki czemu Android Auto buduje własny bezpieczny interfejs na podstawie katalogu aplikacji.

## Uwaga o danych demo

W `stations.json` są przykładowe publiczne strumienie demonstracyjne. Przed publikacją zastąp je stacjami, do których masz prawo udostępniać odnośniki/metadata, najlepiej pobieranymi z Twojego backendu.

## Automatyczny build APK

W paczce jest też `.github/workflows/android.yml`. Po umieszczeniu projektu w GitHub może on zbudować debug APK bez lokalnego wrappera Gradle. Workflow używa JDK 17 i Gradle 9.6.0.

## Stan weryfikacji tej paczki

Kod i konfiguracja zostały przygotowane według aktualnej dokumentacji Android/Media3. W środowisku, w którym wygenerowano paczkę, nie ma Android SDK, dlatego nie wykonano tutaj końcowego `assembleDebug`. Pierwszy Gradle Sync / build należy wykonać w Android Studio albo przez dołączony workflow CI.
