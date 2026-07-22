<?php
/**
 * Plugin Name: Przemyśl Tour – Etap 14 WCAG i wydajność
 * Description: Moduł uzupełniający dla Przemyśl Tour – Wyścigi i Trasy 1.3.0+: WCAG 2.1 AA, mobile, lazy loading map, optymalizacja tabel i konfiguracja Google Maps API.
 * Version: 1.4.0
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * Author: Fundacja Sportowa Przemyśl Tour
 * Text Domain: ptr-stage14
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class PTR_Stage14 {
    const VERSION = '1.4.0';
    const OPTION  = 'ptr_stage14_settings';

    private static $instance = null;

    public static function instance() {
        if ( null === self::$instance ) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        add_action( 'admin_menu', array( $this, 'menu' ), 999 );
        add_action( 'admin_init', array( $this, 'register_settings' ) );
        add_action( 'wp_enqueue_scripts', array( $this, 'frontend_assets' ), 99 );
        add_action( 'admin_enqueue_scripts', array( $this, 'admin_assets' ) );
        add_filter( 'script_loader_tag', array( $this, 'defer_selected_scripts' ), 10, 3 );
        add_filter( 'wp_resource_hints', array( $this, 'resource_hints' ), 10, 2 );
        add_filter( 'body_class', array( $this, 'body_classes' ) );
        add_action( 'wp_head', array( $this, 'skip_link' ), 1 );
        add_action( 'wp_footer', array( $this, 'live_region' ), 1 );
        add_action( 'wp_ajax_ptr_stage14_clear_cache', array( $this, 'clear_cache' ) );
        add_action( 'wp_ajax_ptr_stage14_test_maps', array( $this, 'test_maps' ) );
        add_filter( 'site_status_tests', array( $this, 'site_health_tests' ) );
    }

    public static function defaults() {
        return array(
            'enabled'                 => 1,
            'google_maps_api_key'     => '',
            'google_maps_map_id'      => '',
            'google_maps_language'    => 'pl',
            'google_maps_region'      => 'PL',
            'lazy_maps'               => 1,
            'map_placeholder_height'  => 520,
            'map_load_margin'         => 500,
            'defer_maps'              => 1,
            'cache_minutes'           => 60,
            'results_page_size'       => 50,
            'mobile_results_page_size'=> 25,
            'profile_point_limit'     => 1200,
            'map_point_limit'         => 3000,
            'accessible_tables'       => 1,
            'keyboard_maps'           => 1,
            'reduced_motion'          => 1,
            'high_contrast_focus'     => 1,
            'text_map_alternative'    => 1,
        );
    }

    public function settings() {
        return wp_parse_args( (array) get_option( self::OPTION, array() ), self::defaults() );
    }

    public function register_settings() {
        register_setting(
            'ptr_stage14_group',
            self::OPTION,
            array(
                'type'              => 'array',
                'sanitize_callback' => array( $this, 'sanitize' ),
                'default'           => self::defaults(),
            )
        );
    }

    public function sanitize( $input ) {
        $defaults = self::defaults();
        $out = $defaults;
        $checkboxes = array( 'enabled','lazy_maps','defer_maps','accessible_tables','keyboard_maps','reduced_motion','high_contrast_focus','text_map_alternative' );
        foreach ( $checkboxes as $key ) {
            $out[ $key ] = empty( $input[ $key ] ) ? 0 : 1;
        }
        $out['google_maps_api_key'] = isset( $input['google_maps_api_key'] ) ? sanitize_text_field( $input['google_maps_api_key'] ) : '';
        $out['google_maps_map_id']  = isset( $input['google_maps_map_id'] ) ? sanitize_text_field( $input['google_maps_map_id'] ) : '';
        $out['google_maps_language']= isset( $input['google_maps_language'] ) ? sanitize_key( $input['google_maps_language'] ) : 'pl';
        $out['google_maps_region']  = isset( $input['google_maps_region'] ) ? strtoupper( sanitize_text_field( $input['google_maps_region'] ) ) : 'PL';
        foreach ( array( 'map_placeholder_height','map_load_margin','cache_minutes','results_page_size','mobile_results_page_size','profile_point_limit','map_point_limit' ) as $key ) {
            $out[ $key ] = isset( $input[ $key ] ) ? absint( $input[ $key ] ) : $defaults[ $key ];
        }
        $out['map_placeholder_height']   = min( 1200, max( 240, $out['map_placeholder_height'] ) );
        $out['map_load_margin']          = min( 3000, max( 0, $out['map_load_margin'] ) );
        $out['cache_minutes']            = min( 10080, max( 0, $out['cache_minutes'] ) );
        $out['results_page_size']        = min( 500, max( 10, $out['results_page_size'] ) );
        $out['mobile_results_page_size'] = min( 100, max( 10, $out['mobile_results_page_size'] ) );
        $out['profile_point_limit']      = min( 5000, max( 200, $out['profile_point_limit'] ) );
        $out['map_point_limit']          = min( 10000, max( 500, $out['map_point_limit'] ) );
        return $out;
    }

    public function menu() {
        $parent = $this->find_parent_slug();
        if ( $parent ) {
            add_submenu_page( $parent, 'WCAG, mobile i wydajność', 'WCAG i wydajność', 'manage_options', 'ptr-stage14', array( $this, 'page' ) );
        } else {
            add_menu_page( 'Przemyśl Tour – Etap 14', 'Przemyśl Tour WCAG', 'manage_options', 'ptr-stage14', array( $this, 'page' ), 'dashicons-universal-access-alt', 26 );
        }
    }

    private function find_parent_slug() {
        global $menu;
        foreach ( (array) $menu as $entry ) {
            $label = isset( $entry[0] ) ? wp_strip_all_tags( $entry[0] ) : '';
            $slug  = isset( $entry[2] ) ? (string) $entry[2] : '';
            if ( false !== stripos( $label, 'Przemyśl Tour' ) && 'ptr-stage14' !== $slug ) {
                return $slug;
            }
        }
        return '';
    }

    public function page() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( esc_html__( 'Brak uprawnień.', 'ptr-stage14' ) );
        }
        $s = $this->settings();
        ?>
        <div class="wrap ptr14-admin">
            <h1>Przemyśl Tour – WCAG, mobile i wydajność</h1>
            <p class="description">Etap 14 optymalizuje prezentację map, profili, tabel wyników i formularzy oraz dodaje bezpośrednie odnośniki do konfiguracji Google Maps Platform.</p>
            <form method="post" action="options.php">
                <?php settings_fields( 'ptr_stage14_group' ); ?>
                <div class="ptr14-grid">
                    <section class="ptr14-card ptr14-card--wide">
                        <h2>Google Maps Platform</h2>
                        <p>Do działania map produkcyjnych wymagany jest projekt Google Cloud z włączonym rozliczaniem, aktywnym <strong>Maps JavaScript API</strong> i ograniczonym kluczem API.</p>
                        <div class="ptr14-links">
                            <a class="button button-primary" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/projectcreate">1. Utwórz projekt Google Cloud</a>
                            <a class="button" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/google/maps-apis/overview">2. Otwórz Google Maps Platform</a>
                            <a class="button" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/apis/library/maps-backend.googleapis.com">3. Włącz Maps JavaScript API</a>
                            <a class="button" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/google/maps-apis/credentials">4. Utwórz klucz API</a>
                            <a class="button" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/google/maps-apis/studio/maps">5. Utwórz Map ID</a>
                            <a class="button" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/billing">6. Skonfiguruj rozliczenia</a>
                            <a class="button" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/google/maps-apis/quotas">7. Limity i wykorzystanie</a>
                        </div>
                        <div class="notice notice-warning inline"><p><strong>Wymagane ograniczenia klucza:</strong> ustaw „Websites” / HTTP referrers i dodaj domenę produkcyjną oraz staging, np. <code>https://twoja-domena.pl/*</code>. W ograniczeniach API pozostaw co najmniej <strong>Maps JavaScript API</strong>. Nie używaj nieograniczonego klucza.</p></div>
                        <table class="form-table" role="presentation">
                            <tr><th><label for="ptr14-key">Klucz Google Maps API</label></th><td><input id="ptr14-key" class="regular-text code" type="password" autocomplete="new-password" name="<?php echo esc_attr( self::OPTION ); ?>[google_maps_api_key]" value="<?php echo esc_attr( $s['google_maps_api_key'] ); ?>"><button type="button" class="button ptr14-toggle-secret" data-target="ptr14-key">Pokaż</button><p class="description">Klucz przeznaczony dla przeglądarki, zabezpieczony ograniczeniem domenowym.</p></td></tr>
                            <tr><th><label for="ptr14-map-id">Google Maps Map ID</label></th><td><input id="ptr14-map-id" class="regular-text code" type="text" name="<?php echo esc_attr( self::OPTION ); ?>[google_maps_map_id]" value="<?php echo esc_attr( $s['google_maps_map_id'] ); ?>"><p class="description">Map ID jest potrzebny do Advanced Markers i stylowania map w chmurze.</p></td></tr>
                            <tr><th><label for="ptr14-language">Język mapy</label></th><td><input id="ptr14-language" type="text" size="6" name="<?php echo esc_attr( self::OPTION ); ?>[google_maps_language]" value="<?php echo esc_attr( $s['google_maps_language'] ); ?>"> <label>Region <input type="text" size="6" name="<?php echo esc_attr( self::OPTION ); ?>[google_maps_region]" value="<?php echo esc_attr( $s['google_maps_region'] ); ?>"></label></td></tr>
                        </table>
                        <p><button type="button" class="button ptr14-test-maps">Sprawdź konfigurację</button> <span class="ptr14-test-result" aria-live="polite"></span></p>
                    </section>

                    <section class="ptr14-card">
                        <h2>Mapy i profile</h2>
                        <?php $this->checkbox( 'lazy_maps', 'Ładuj mapy dopiero przed wejściem do widoku', $s ); ?>
                        <?php $this->checkbox( 'defer_maps', 'Ładuj skrypt Google Maps z defer', $s ); ?>
                        <?php $this->checkbox( 'keyboard_maps', 'Włącz klawiaturową obsługę map i profili', $s ); ?>
                        <?php $this->checkbox( 'text_map_alternative', 'Pokazuj tekstową alternatywę mapy', $s ); ?>
                        <?php $this->number( 'map_placeholder_height', 'Wysokość placeholdera mapy (px)', $s, 240, 1200 ); ?>
                        <?php $this->number( 'map_load_margin', 'Wyprzedzenie lazy load (px)', $s, 0, 3000 ); ?>
                        <?php $this->number( 'map_point_limit', 'Maks. punktów mapy', $s, 500, 10000 ); ?>
                        <?php $this->number( 'profile_point_limit', 'Maks. punktów profilu', $s, 200, 5000 ); ?>
                    </section>

                    <section class="ptr14-card">
                        <h2>WCAG 2.1 AA</h2>
                        <?php $this->checkbox( 'accessible_tables', 'Responsywne tabele z etykietami komórek', $s ); ?>
                        <?php $this->checkbox( 'reduced_motion', 'Respektuj prefers-reduced-motion', $s ); ?>
                        <?php $this->checkbox( 'high_contrast_focus', 'Wzmocniony widoczny fokus', $s ); ?>
                        <p>Moduł dodaje skip link, region komunikatów aria-live, minimalne pola dotykowe 44×44 px, poprawione kontrasty i czytelny widok kartowy tabel na telefonach.</p>
                    </section>

                    <section class="ptr14-card">
                        <h2>Wyniki i duże dane</h2>
                        <?php $this->number( 'results_page_size', 'Wierszy wyników na desktopie', $s, 10, 500 ); ?>
                        <?php $this->number( 'mobile_results_page_size', 'Wierszy wyników na mobile', $s, 10, 100 ); ?>
                        <?php $this->number( 'cache_minutes', 'Cache danych (minuty)', $s, 0, 10080 ); ?>
                        <p class="description">Ustawienia są dostępne przez filtry PHP, dzięki czemu główna wtyczka może używać ich bez twardej zależności.</p>
                    </section>

                    <section class="ptr14-card">
                        <h2>Narzędzia</h2>
                        <p><button type="button" class="button ptr14-clear-cache">Wyczyść cache Przemyśl Tour</button></p>
                        <p class="description ptr14-cache-result" aria-live="polite"></p>
                        <p><a href="<?php echo esc_url( admin_url( 'site-health.php' ) ); ?>">Otwórz Stan witryny</a></p>
                    </section>
                </div>
                <?php submit_button( 'Zapisz ustawienia Etapu 14' ); ?>
            </form>
        </div>
        <?php
    }

    private function checkbox( $key, $label, $s ) {
        echo '<label class="ptr14-check"><input type="checkbox" name="' . esc_attr( self::OPTION ) . '[' . esc_attr( $key ) . ']" value="1" ' . checked( ! empty( $s[ $key ] ), true, false ) . '> <span>' . esc_html( $label ) . '</span></label>';
    }

    private function number( $key, $label, $s, $min, $max ) {
        echo '<label class="ptr14-number"><span>' . esc_html( $label ) . '</span><input type="number" min="' . esc_attr( $min ) . '" max="' . esc_attr( $max ) . '" name="' . esc_attr( self::OPTION ) . '[' . esc_attr( $key ) . ']" value="' . esc_attr( $s[ $key ] ) . '"></label>';
    }

    public function frontend_assets() {
        $s = $this->settings();
        if ( empty( $s['enabled'] ) ) {
            return;
        }
        wp_register_style( 'ptr-stage14', false, array(), self::VERSION );
        wp_enqueue_style( 'ptr-stage14' );
        wp_add_inline_style( 'ptr-stage14', $this->frontend_css( $s ) );
        wp_register_script( 'ptr-stage14', '', array(), self::VERSION, true );
        wp_enqueue_script( 'ptr-stage14' );
        wp_add_inline_script( 'ptr-stage14', 'window.PTRStage14=' . wp_json_encode( array(
            'lazyMaps' => (bool) $s['lazy_maps'],
            'loadMargin' => (int) $s['map_load_margin'],
            'accessibleTables' => (bool) $s['accessible_tables'],
            'keyboardMaps' => (bool) $s['keyboard_maps'],
            'mobilePageSize' => (int) $s['mobile_results_page_size'],
            'desktopPageSize' => (int) $s['results_page_size'],
        ) ) . ';' . $this->frontend_js(), 'before' );

        add_filter( 'ptr_google_maps_api_key', function( $key ) use ( $s ) { return $s['google_maps_api_key'] ? $s['google_maps_api_key'] : $key; } );
        add_filter( 'ptr_google_maps_map_id', function( $id ) use ( $s ) { return $s['google_maps_map_id'] ? $s['google_maps_map_id'] : $id; } );
        add_filter( 'ptr_results_per_page', function() use ( $s ) { return (int) $s['results_page_size']; } );
        add_filter( 'ptr_results_mobile_per_page', function() use ( $s ) { return (int) $s['mobile_results_page_size']; } );
        add_filter( 'ptr_route_map_point_limit', function() use ( $s ) { return (int) $s['map_point_limit']; } );
        add_filter( 'ptr_route_profile_point_limit', function() use ( $s ) { return (int) $s['profile_point_limit']; } );
        add_filter( 'ptr_cache_ttl', function() use ( $s ) { return (int) $s['cache_minutes'] * MINUTE_IN_SECONDS; } );
    }

    private function frontend_css( $s ) {
        $height = (int) $s['map_placeholder_height'];
        return ":root{--ptr-focus:#005fcc;--ptr-focus-offset:3px;--ptr-border:#d7dde5;--ptr-muted:#52606d;--ptr-card:#fff;--ptr-danger:#b42318}html{scroll-behavior:smooth}.ptr-skip-link{position:fixed;left:1rem;top:1rem;z-index:999999;transform:translateY(-180%);background:#fff;color:#111;padding:.75rem 1rem;border:3px solid var(--ptr-focus);border-radius:.35rem;font-weight:700}.ptr-skip-link:focus{transform:none}.ptr-live-region{position:absolute!important;width:1px!important;height:1px!important;padding:0!important;margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;border:0!important}.ptr-map,.ptr-route-map,.ptr-map-canvas,[data-ptr-map]{min-height:{$height}px;background:#eef2f6;position:relative}.ptr-map[data-ptr-lazy-pending]::before,.ptr-route-map[data-ptr-lazy-pending]::before,[data-ptr-map][data-ptr-lazy-pending]::before{content:'Mapa zostanie załadowana po przewinięciu';position:absolute;inset:0;display:grid;place-items:center;padding:2rem;text-align:center;color:#263238;font-weight:700}.ptr-map button,.ptr-route-explorer button,.ptr-results button,.ptr-registration-form button,.ptr-button{min-width:44px;min-height:44px}.ptr-route-explorer :is(a,button,input,select,textarea):focus-visible,.ptr-results :is(a,button,input,select,textarea):focus-visible,.ptr-registration-form :is(a,button,input,select,textarea):focus-visible,.ptr-content-feed :is(a,button):focus-visible{outline:3px solid var(--ptr-focus)!important;outline-offset:var(--ptr-focus-offset)!important;box-shadow:none!important}.ptr-table-wrap,.ptr-results-table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}.ptr-results table,.ptr-start-list table,.ptr-route-points-table{border-collapse:collapse;width:100%}.ptr-results th,.ptr-results td,.ptr-start-list th,.ptr-start-list td,.ptr-route-points-table th,.ptr-route-points-table td{padding:.75rem;border:1px solid var(--ptr-border);text-align:left}.ptr-results th,.ptr-start-list th,.ptr-route-points-table th{background:#f2f4f7;color:#17202a}.ptr-visually-hidden{position:absolute!important;width:1px!important;height:1px!important;padding:0!important;margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;border:0!important}@media(max-width:782px){.ptr-results table,.ptr-results thead,.ptr-results tbody,.ptr-results tr,.ptr-results th,.ptr-results td,.ptr-start-list table,.ptr-start-list thead,.ptr-start-list tbody,.ptr-start-list tr,.ptr-start-list th,.ptr-start-list td{display:block}.ptr-results thead,.ptr-start-list thead{position:absolute!important;width:1px!important;height:1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important}.ptr-results tr,.ptr-start-list tr{margin:0 0 1rem;background:var(--ptr-card);border:1px solid var(--ptr-border);border-radius:.6rem;padding:.5rem}.ptr-results td,.ptr-start-list td{display:grid;grid-template-columns:minmax(8rem,42%) 1fr;gap:.75rem;border:0;border-bottom:1px solid #edf0f3;padding:.65rem}.ptr-results td:last-child,.ptr-start-list td:last-child{border-bottom:0}.ptr-results td::before,.ptr-start-list td::before{content:attr(data-label);font-weight:700;color:#344054}.ptr-route-explorer,.ptr-race-card,.ptr-route-card{max-width:100%;overflow:hidden}.ptr-map,.ptr-route-map,.ptr-map-canvas,[data-ptr-map]{min-height:min({$height}px,70vh)}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto!important}*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}@media(forced-colors:active){.ptr-route-explorer :is(a,button,input,select,textarea):focus-visible{outline:3px solid CanvasText!important}.ptr-map,.ptr-route-map,[data-ptr-map]{border:2px solid CanvasText}}";
    }

    private function frontend_js() {
        return <<<'JS'
(function(){
'use strict';
var cfg=window.PTRStage14||{};
function announce(text){var r=document.querySelector('.ptr-live-region');if(r){r.textContent='';setTimeout(function(){r.textContent=text;},20);}}
function labelTables(){if(!cfg.accessibleTables)return;document.querySelectorAll('.ptr-results table,.ptr-start-list table,.ptr-route-points-table').forEach(function(table){var headers=[].map.call(table.querySelectorAll('thead th'),function(th){return th.textContent.trim();});table.querySelectorAll('tbody tr').forEach(function(row){row.querySelectorAll('td').forEach(function(td,i){if(!td.hasAttribute('data-label'))td.setAttribute('data-label',headers[i]||'Dane');});});});}
function prepareMaps(){var maps=document.querySelectorAll('.ptr-map,.ptr-route-map,.ptr-map-canvas,[data-ptr-map]');if(!maps.length)return;if(!cfg.lazyMaps){maps.forEach(function(m){m.dispatchEvent(new CustomEvent('ptr:map-visible',{bubbles:true}));});return;}var observer=new IntersectionObserver(function(entries,obs){entries.forEach(function(e){if(!e.isIntersecting)return;var m=e.target;m.removeAttribute('data-ptr-lazy-pending');m.dispatchEvent(new CustomEvent('ptr:map-visible',{bubbles:true}));if(typeof window.PTRInitMap==='function')window.PTRInitMap(m);obs.unobserve(m);});},{rootMargin:(cfg.loadMargin||500)+'px 0px'});maps.forEach(function(m){m.setAttribute('data-ptr-lazy-pending','1');observer.observe(m);});}
function keyboardMaps(){if(!cfg.keyboardMaps)return;document.querySelectorAll('.ptr-map,.ptr-route-map,.ptr-map-canvas,[data-ptr-map]').forEach(function(map){if(!map.hasAttribute('tabindex'))map.setAttribute('tabindex','0');if(!map.hasAttribute('role'))map.setAttribute('role','region');if(!map.hasAttribute('aria-label'))map.setAttribute('aria-label','Interaktywna mapa trasy. Użyj klawiszy strzałek do obsługi, a pod mapą znajduje się alternatywa tekstowa.');map.addEventListener('keydown',function(e){if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Home','End'].indexOf(e.key)!==-1){map.dispatchEvent(new CustomEvent('ptr:map-key',{bubbles:true,detail:{key:e.key}}));announce('Zmieniono położenie na mapie.');}});});}
function paginateLargeTables(){document.querySelectorAll('.ptr-results table tbody').forEach(function(tbody){var rows=[].slice.call(tbody.children);var size=window.matchMedia('(max-width:782px)').matches?(cfg.mobilePageSize||25):(cfg.desktopPageSize||50);if(rows.length<=size)return;var page=1,total=Math.ceil(rows.length/size);var nav=document.createElement('nav');nav.className='ptr-client-pagination';nav.setAttribute('aria-label','Stronicowanie wyników');var prev=document.createElement('button'),next=document.createElement('button'),status=document.createElement('span');prev.type=next.type='button';prev.textContent='Poprzednia';next.textContent='Następna';nav.append(prev,status,next);tbody.parentNode.parentNode.appendChild(nav);function render(){rows.forEach(function(r,i){r.hidden=!(i>=(page-1)*size&&i<page*size);});status.textContent=' Strona '+page+' z '+total+' ';prev.disabled=page===1;next.disabled=page===total;}prev.addEventListener('click',function(){if(page>1){page--;render();announce('Strona '+page+' wyników');}});next.addEventListener('click',function(){if(page<total){page++;render();announce('Strona '+page+' wyników');}});render();});}
function externalLinks(){document.querySelectorAll('.ptr-content a[target="_blank"],.ptr-route-explorer a[target="_blank"]').forEach(function(a){if(!a.querySelector('.ptr-visually-hidden')){var s=document.createElement('span');s.className='ptr-visually-hidden';s.textContent=' (otwiera się w nowej karcie)';a.appendChild(s);}});}
function init(){labelTables();prepareMaps();keyboardMaps();paginateLargeTables();externalLinks();document.dispatchEvent(new CustomEvent('ptr:stage14-ready'));}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
JS;
    }

    public function defer_selected_scripts( $tag, $handle, $src ) {
        $s = $this->settings();
        if ( empty( $s['defer_maps'] ) ) {
            return $tag;
        }
        if ( false !== strpos( $src, 'maps.googleapis.com/maps/api/js' ) || false !== strpos( $handle, 'ptr-map' ) || false !== strpos( $handle, 'google-map' ) ) {
            if ( false === strpos( $tag, ' defer' ) ) {
                $tag = str_replace( '<script ', '<script defer ', $tag );
            }
        }
        return $tag;
    }

    public function resource_hints( $urls, $relation_type ) {
        if ( in_array( $relation_type, array( 'preconnect', 'dns-prefetch' ), true ) ) {
            $urls[] = 'https://maps.googleapis.com';
            $urls[] = 'https://maps.gstatic.com';
        }
        return array_unique( $urls );
    }

    public function body_classes( $classes ) {
        $s = $this->settings();
        $classes[] = 'ptr-stage14';
        if ( ! empty( $s['high_contrast_focus'] ) ) $classes[] = 'ptr-strong-focus';
        if ( ! empty( $s['reduced_motion'] ) ) $classes[] = 'ptr-reduced-motion-ready';
        return $classes;
    }

    public function skip_link() {
        echo '<a class="ptr-skip-link" href="#main">Przejdź do głównej treści</a>';
    }

    public function live_region() {
        echo '<div class="ptr-live-region" role="status" aria-live="polite" aria-atomic="true"></div>';
    }

    public function admin_assets( $hook ) {
        if ( false === strpos( (string) $hook, 'ptr-stage14' ) ) return;
        wp_register_style( 'ptr-stage14-admin', false, array(), self::VERSION );
        wp_enqueue_style( 'ptr-stage14-admin' );
        wp_add_inline_style( 'ptr-stage14-admin', '.ptr14-admin{max-width:1280px}.ptr14-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:20px}.ptr14-card{background:#fff;border:1px solid #dcdcde;border-radius:8px;padding:20px;box-shadow:0 1px 2px rgba(0,0,0,.04)}.ptr14-card--wide{grid-column:1/-1}.ptr14-card h2{margin-top:0}.ptr14-links{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}.ptr14-check{display:flex;gap:8px;align-items:flex-start;margin:12px 0;font-weight:600}.ptr14-number{display:grid;grid-template-columns:1fr 110px;gap:12px;align-items:center;margin:12px 0}.ptr14-number input{width:100%}.ptr14-test-result.is-ok{color:#008a20;font-weight:700}.ptr14-test-result.is-error{color:#b32d2e;font-weight:700}@media(max-width:782px){.ptr14-grid{grid-template-columns:1fr}.ptr14-card--wide{grid-column:auto}.ptr14-links .button{width:100%;text-align:center}.ptr14-number{grid-template-columns:1fr}}' );
        wp_register_script( 'ptr-stage14-admin', '', array( 'jquery' ), self::VERSION, true );
        wp_enqueue_script( 'ptr-stage14-admin' );
        wp_add_inline_script( 'ptr-stage14-admin', 'window.PTR14Admin=' . wp_json_encode( array( 'ajaxUrl'=>admin_url('admin-ajax.php'),'nonce'=>wp_create_nonce('ptr_stage14_admin') ) ) . ';' . <<<'JS'
(function($){
$('.ptr14-toggle-secret').on('click',function(){var el=document.getElementById($(this).data('target'));if(!el)return;el.type=el.type==='password'?'text':'password';$(this).text(el.type==='password'?'Pokaż':'Ukryj');});
$('.ptr14-clear-cache').on('click',function(){var b=$(this).prop('disabled',true);$('.ptr14-cache-result').text('Czyszczenie…');$.post(PTR14Admin.ajaxUrl,{action:'ptr_stage14_clear_cache',nonce:PTR14Admin.nonce}).done(function(r){$('.ptr14-cache-result').text(r.data&&r.data.message?r.data.message:'Gotowe.');}).always(function(){b.prop('disabled',false);});});
$('.ptr14-test-maps').on('click',function(){var b=$(this).prop('disabled',true),o=$('.ptr14-test-result').removeClass('is-ok is-error').text('Sprawdzanie…');$.post(PTR14Admin.ajaxUrl,{action:'ptr_stage14_test_maps',nonce:PTR14Admin.nonce,key:$('#ptr14-key').val(),map_id:$('#ptr14-map-id').val()}).done(function(r){o.addClass(r.success?'is-ok':'is-error').text(r.data&&r.data.message?r.data.message:'Brak odpowiedzi.');}).fail(function(){o.addClass('is-error').text('Nie udało się wykonać testu.');}).always(function(){b.prop('disabled',false);});});
})(jQuery);
JS
        );
    }

    public function clear_cache() {
        check_ajax_referer( 'ptr_stage14_admin', 'nonce' );
        if ( ! current_user_can( 'manage_options' ) ) wp_send_json_error( array( 'message'=>'Brak uprawnień.' ), 403 );
        global $wpdb;
        $like1 = $wpdb->esc_like( '_transient_ptr_' ) . '%';
        $like2 = $wpdb->esc_like( '_transient_timeout_ptr_' ) . '%';
        $deleted = (int) $wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s OR option_name LIKE %s", $like1, $like2 ) );
        wp_send_json_success( array( 'message'=>sprintf( 'Usunięto %d wpisów cache.', max(0,$deleted) ) ) );
    }

    public function test_maps() {
        check_ajax_referer( 'ptr_stage14_admin', 'nonce' );
        if ( ! current_user_can( 'manage_options' ) ) wp_send_json_error( array( 'message'=>'Brak uprawnień.' ), 403 );
        $key = isset($_POST['key']) ? sanitize_text_field( wp_unslash($_POST['key']) ) : '';
        $map_id = isset($_POST['map_id']) ? sanitize_text_field( wp_unslash($_POST['map_id']) ) : '';
        if ( ! $key ) wp_send_json_error( array( 'message'=>'Wprowadź klucz API.' ) );
        if ( strlen($key) < 20 ) wp_send_json_error( array( 'message'=>'Klucz wygląda na niepełny.' ) );
        $message = 'Format klucza jest poprawny. Zapisz ustawienia i sprawdź mapę na froncie.';
        if ( ! $map_id ) $message .= ' Map ID jest puste – klasyczna mapa zadziała, ale Advanced Markers mogą być niedostępne.';
        wp_send_json_success( array( 'message'=>$message ) );
    }

    public function site_health_tests( $tests ) {
        $tests['direct']['ptr_stage14_maps'] = array( 'label'=>'Przemyśl Tour: Google Maps i WCAG', 'test'=>array($this,'health_test') );
        return $tests;
    }

    public function health_test() {
        $s = $this->settings();
        $ok = ! empty( $s['google_maps_api_key'] ) && ! empty( $s['lazy_maps'] ) && ! empty( $s['accessible_tables'] );
        return array(
            'label' => $ok ? 'Konfiguracja map i dostępności jest aktywna' : 'Konfiguracja map lub dostępności wymaga uzupełnienia',
            'status' => $ok ? 'good' : 'recommended',
            'badge' => array( 'label'=>'Przemyśl Tour', 'color'=>'blue' ),
            'description' => '<p>' . ( $ok ? 'Klucz mapy, lazy loading i responsywne tabele są skonfigurowane.' : 'Sprawdź klucz Google Maps API oraz ustawienia WCAG w Przemyśl Tour → WCAG i wydajność.' ) . '</p>',
            'actions' => '<p><a href="' . esc_url( admin_url('admin.php?page=ptr-stage14') ) . '">Otwórz ustawienia Etapu 14</a></p>',
            'test' => 'ptr_stage14_maps',
        );
    }
}

PTR_Stage14::instance();
