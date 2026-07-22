# Przemyśl Tour – Etap 14

Moduł uzupełniający dla wtyczki **Przemyśl Tour – Wyścigi i Trasy 1.3.0+**.

## Zakres

- WCAG 2.1 AA: skip link, aria-live, widoczny fokus, obsługa klawiatury, reduced motion, forced colors.
- Mobile: tabele wyników i list startowych zmieniane w karty, minimalne pola dotykowe 44×44 px.
- Wydajność: lazy loading map, defer Google Maps, preconnect, ograniczenia liczby punktów mapy i profilu, cache.
- Konfiguracja Google Maps: klucz API, Map ID, język i region, oficjalne linki do Google Cloud Console.
- Diagnostyka w WordPress Site Health.

## Instalacja

1. Pobierz katalog `przemysl-tour-stage14`.
2. Skopiuj go do `/wp-content/plugins/` albo spakuj sam katalog do ZIP i wgraj w WordPressie.
3. Aktywuj **Przemyśl Tour – Etap 14 WCAG i wydajność**.
4. Otwórz `Przemyśl Tour → WCAG i wydajność`.
5. Uzupełnij klucz Google Maps i opcjonalny Map ID.

## Google Maps

1. Utwórz projekt: https://console.cloud.google.com/projectcreate
2. Google Maps Platform: https://console.cloud.google.com/google/maps-apis/overview
3. Włącz Maps JavaScript API: https://console.cloud.google.com/apis/library/maps-backend.googleapis.com
4. Utwórz klucz API: https://console.cloud.google.com/google/maps-apis/credentials
5. Utwórz Map ID: https://console.cloud.google.com/google/maps-apis/studio/maps
6. Rozliczenia: https://console.cloud.google.com/billing
7. Limity i wykorzystanie: https://console.cloud.google.com/google/maps-apis/quotas

Dla klucza ustaw ograniczenie aplikacji **Websites / HTTP referrers** i dodaj domeny w formie `https://example.com/*`. Następnie ogranicz klucz do **Maps JavaScript API**.

## Integracja

Moduł udostępnia filtry:

- `ptr_google_maps_api_key`
- `ptr_google_maps_map_id`
- `ptr_results_per_page`
- `ptr_results_mobile_per_page`
- `ptr_route_map_point_limit`
- `ptr_route_profile_point_limit`
- `ptr_cache_ttl`

Główna wtyczka może korzystać z nich bez twardej zależności.
