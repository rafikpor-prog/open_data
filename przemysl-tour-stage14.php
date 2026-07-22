<?php
/**
 * Plugin Name: Przemyśl Tour – Etap 14 WCAG i wydajność
 * Description: Moduł uzupełniający dla Przemyśl Tour – Wyścigi i Trasy 1.3.0+: WCAG 2.1 AA, mobile, lazy loading map, optymalizacja tabel i konfiguracja Google Maps API.
 * Version: 1.4.1
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * Author: Fundacja Sportowa Przemyśl Tour
 * Text Domain: ptr-stage14
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class PTR_Stage14_Fixed {
    const VERSION = '1.4.1';
    const OPTION  = 'ptr_stage14_settings';
    const NONCE   = 'ptr_stage14_admin';

    private static $instance = null;

    public static function instance() {
        if ( null === self::$instance ) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        add_action( 'admin_menu', array( $this, 'register_menu' ), 999 );
        add_action( 'admin_init', array( $this, 'register_settings' ) );
        add_action( 'wp_enqueue_scripts', array( $this, 'frontend_assets' ), 99 );
        add_action( 'admin_enqueue_scripts', array( $this, 'admin_assets' ) );
        add_action( 'wp_body_open', array( $this, 'render_skip_link' ), 1 );
        add_action( 'wp_footer', array( $this, 'render_live_region' ), 1 );
        add_action( 'wp_ajax_ptr_stage14_clear_cache', array( $this, 'clear_cache' ) );
        add_action( 'wp_ajax_ptr_stage14_test_maps', array( $this, 'test_maps' ) );
        add_filter( 'script_loader_tag', array( $this, 'defer_maps_script' ), 10, 3 );
        add_filter( 'wp_resource_hints', array( $this, 'resource_hints' ), 10, 2 );
        add_filter( 'body_class', array( $this, 'body_classes' ) );
        add_filter( 'site_status_tests', array( $this, 'site_health_tests' ) );

        add_filter( 'ptr_google_maps_api_key', array( $this, 'filter_maps_key' ) );
        add_filter( 'ptr_google_maps_map_id', array( $this, 'filter_map_id' ) );
        add_filter( 'ptr_results_per_page', array( $this, 'filter_results_page_size' ) );
        add_filter( 'ptr_results_mobile_per_page', array( $this, 'filter_mobile_results_page_size' ) );
        add_filter( 'ptr_route_map_point_limit', array( $this, 'filter_map_point_limit' ) );
        add_filter( 'ptr_route_profile_point_limit', array( $this, 'filter_profile_point_limit' ) );
        add_filter( 'ptr_cache_ttl', array( $this, 'filter_cache_ttl' ) );
    }

    public static function defaults() {
        return array(
            'enabled'                  => 1,
            'google_maps_api_key'      => '',
            'google_maps_map_id'       => '',
            'google_maps_language'     => 'pl',
            'google_maps_region'       => 'PL',
            'lazy_maps'                => 1,
            'map_placeholder_height'   => 520,
            'map_load_margin'          => 500,
            'defer_maps'               => 1,
            'cache_minutes'            => 60,
            'results_page_size'        => 50,
            'mobile_results_page_size' => 25,
            'profile_point_limit'      => 1200,
            'map_point_limit'          => 3000,
            'accessible_tables'        => 1,
            'keyboard_maps'            => 1,
            'reduced_motion'           => 1,
            'high_contrast_focus'      => 1,
            'text_map_alternative'     => 1,
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
                'sanitize_callback' => array( $this, 'sanitize_settings' ),
                'default'           => self::defaults(),
            )
        );
    }

    public function sanitize_settings( $input ) {
        $input    = is_array( $input ) ? $input : array();
        $defaults = self::defaults();
        $output   = $defaults;

        $checkboxes = array(
            'enabled', 'lazy_maps', 'defer_maps', 'accessible_tables',
            'keyboard_maps', 'reduced_motion', 'high_contrast_focus',
            'text_map_alternative',
        );
        foreach ( $checkboxes as $key ) {
            $output[ $key ] = empty( $input[ $key ] ) ? 0 : 1;
        }

        $output['google_maps_api_key']  = isset( $input['google_maps_api_key'] ) ? sanitize_text_field( $input['google_maps_api_key'] ) : '';
        $output['google_maps_map_id']   = isset( $input['google_maps_map_id'] ) ? sanitize_text_field( $input['google_maps_map_id'] ) : '';
        $output['google_maps_language'] = isset( $input['google_maps_language'] ) ? sanitize_key( $input['google_maps_language'] ) : 'pl';
        $output['google_maps_region']   = isset( $input['google_maps_region'] ) ? strtoupper( sanitize_text_field( $input['google_maps_region'] ) ) : 'PL';

        $limits = array(
            'map_placeholder_height'   => array( 240, 1200 ),
            'map_load_margin'          => array( 0, 3000 ),
            'cache_minutes'            => array( 0, 10080 ),
            'results_page_size'        => array( 10, 500 ),
            'mobile_results_page_size' => array( 10, 100 ),
            'profile_point_limit'      => array( 200, 5000 ),
            'map_point_limit'          => array( 500, 10000 ),
        );
        foreach ( $limits as $key => $range ) {
            $value          = isset( $input[ $key ] ) ? absint( $input[ $key ] ) : $defaults[ $key ];
            $output[ $key ] = min( $range[1], max( $range[0], $value ) );
        }

        return $output;
    }

    public function register_menu() {
        $parent = $this->find_parent_slug();
        if ( $parent ) {
            add_submenu_page(
                $parent,
                'WCAG, mobile i wydajność',
                'WCAG i wydajność',
                'manage_options',
                'ptr-stage14',
                array( $this, 'render_settings_page' )
            );
            return;
        }

        add_menu_page(
            'Przemyśl Tour – WCAG i wydajność',
            'Przemyśl Tour WCAG',
            'manage_options',
            'ptr-stage14',
            array( $this, 'render_settings_page' ),
            'dashicons-universal-access-alt',
            26
        );
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

    public function render_settings_page() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( esc_html__( 'Brak uprawnień.', 'ptr-stage14' ) );
        }
        $settings = $this->settings();
        ?>
        <div class="wrap ptr14-admin">
            <h1>Przemyśl Tour – WCAG, mobile i wydajność</h1>
            <p class="description">Ustawienia dostępności, optymalizacji map i dużych tabel oraz bezpośrednie odnośniki do Google Maps Platform.</p>

            <form method="post" action="options.php">
                <?php settings_fields( 'ptr_stage14_group' ); ?>
                <div class="ptr14-grid">
                    <section class="ptr14-card ptr14-card--wide">
                        <h2>Google Maps Platform</h2>
                        <p>Wymagany jest projekt Google Cloud, aktywne rozliczanie, włączone <strong>Maps JavaScript API</strong> i klucz ograniczony do domeny serwisu.</p>
                        <div class="ptr14-links">
                            <a class="button button-primary" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/projectcreate">1. Utwórz projekt</a>
                            <a class="button" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/google/maps-apis/overview">2. Maps Platform</a>
                            <a class="button" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/apis/library/maps-backend.googleapis.com">3. Włącz Maps JavaScript API</a>
                            <a class="button" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/google/maps-apis/credentials">4. Utwórz klucz API</a>
                            <a class="button" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/google/maps-apis/studio/maps">5. Utwórz Map ID</a>
                            <a class="button" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/billing">6. Rozliczenia</a>
                            <a class="button" target="_blank" rel="noopener noreferrer" href="https://console.cloud.google.com/google/maps-apis/quotas">7. Limity i użycie</a>
                        </div>
                        <div class="notice notice-warning inline"><p><strong>Zabezpiecz klucz:</strong> wybierz ograniczenie „Websites / HTTP referrers”, dodaj domenę produkcyjną i staging, np. <code>https://twoja-domena.pl/*</code>, a w ograniczeniach API pozostaw <strong>Maps JavaScript API</strong>.</p></div>
                        <table class="form-table" role="presentation">
                            <tr>
                                <th><label for="ptr14-key">Klucz Google Maps API</label></th>
                                <td><input id="ptr14-key" class="regular-text code" type="password" autocomplete="new-password" name="<?php echo esc_attr( self::OPTION ); ?>[google_maps_api_key]" value="<?php echo esc_attr( $settings['google_maps_api_key'] ); ?>"> <button type="button" class="button ptr14-toggle-secret" data-target="ptr14-key">Pokaż</button></td>
                            </tr>
                            <tr>
                                <th><label for="ptr14-map-id">Google Maps Map ID</label></th>
                                <td><input id="ptr14-map-id" class="regular-text code" type="text" name="<?php echo esc_attr( self::OPTION ); ?>[google_maps_map_id]" value="<?php echo esc_attr( $settings['google_maps_map_id'] ); ?>"></td>
                            </tr>
                            <tr>
                                <th><label for="ptr14-language">Język i region</label></th>
                                <td><input id="ptr14-language" type="text" size="6" name="<?php echo esc_attr( self::OPTION ); ?>[google_maps_language]" value="<?php echo esc_attr( $settings['google_maps_language'] ); ?>"> <input type="text" size="6" name="<?php echo esc_attr( self::OPTION ); ?>[google_maps_region]" value="<?php echo esc_attr( $settings['google_maps_region'] ); ?>"></td>
                            </tr>
                        </table>
                        <p><button type="button" class="button ptr14-test-maps">Sprawdź format konfiguracji</button> <span class="ptr14-test-result" aria-live="polite"></span></p>
                    </section>

                    <section class="ptr14-card">
                        <h2>Mapy i profile</h2>
                        <?php $this->checkbox( 'lazy_maps', 'Ładuj mapy przed wejściem do widoku', $settings ); ?>
                        <?php $this->checkbox( 'defer_maps', 'Dodaj defer do skryptu Google Maps', $settings ); ?>
                        <?php $this->checkbox( 'keyboard_maps', 'Klawiaturowa obsługa map', $settings ); ?>
                        <?php $this->checkbox( 'text_map_alternative', 'Tekstowa alternatywa mapy', $settings ); ?>
                        <?php $this->number( 'map_placeholder_height', 'Wysokość mapy (px)', $settings, 240, 1200 ); ?>
                        <?php $this->number( 'map_load_margin', 'Wyprzedzenie lazy load (px)', $settings, 0, 3000 ); ?>
                        <?php $this->number( 'map_point_limit', 'Maks. punktów mapy', $settings, 500, 10000 ); ?>
                        <?php $this->number( 'profile_point_limit', 'Maks. punktów profilu', $settings, 200, 5000 ); ?>
                    </section>

                    <section class="ptr14-card">
                        <h2>WCAG 2.1 AA</h2>
                        <?php $this->checkbox( 'accessible_tables', 'Responsywne tabele z etykietami', $settings ); ?>
                        <?php $this->checkbox( 'reduced_motion', 'Respektuj prefers-reduced-motion', $settings ); ?>
                        <?php $this->checkbox( 'high_contrast_focus', 'Wzmocniony fokus klawiatury', $settings ); ?>
                        <p>Moduł dodaje skip link, region aria-live, pola dotykowe minimum 44 × 44 px oraz mobilny układ kartowy wyników.</p>
                    </section>

                    <section class="ptr14-card">
                        <h2>Wyniki i cache</h2>
                        <?php $this->number( 'results_page_size', 'Wyników na desktopie', $settings, 10, 500 ); ?>
                        <?php $this->number( 'mobile_results_page_size', 'Wyników na mobile', $settings, 10, 100 ); ?>
                        <?php $this->number( 'cache_minutes', 'Cache danych (minuty)', $settings, 0, 10080 ); ?>
                        <p><button type="button" class="button ptr14-clear-cache">Wyczyść cache Przemyśl Tour</button></p>
                        <p class="ptr14-cache-result" aria-live="polite"></p>
                    </section>
                </div>
                <?php submit_button( 'Zapisz ustawienia' ); ?>
            </form>
        </div>
        <?php
    }

    private function checkbox( $key, $label, $settings ) {
        echo '<label class="ptr14-check"><input type="checkbox" name="' . esc_attr( self::OPTION ) . '[' . esc_attr( $key ) . ']" value="1" ' . checked( ! empty( $settings[ $key ] ), true, false ) . '> <span>' . esc_html( $label ) . '</span></label>';
    }

    private function number( $key, $label, $settings, $min, $max ) {
        echo '<label class="ptr14-number"><span>' . esc_html( $label ) . '</span><input type="number" min="' . esc_attr( $min ) . '" max="' . esc_attr( $max ) . '" name="' . esc_attr( self::OPTION ) . '[' . esc_attr( $key ) . ']" value="' . esc_attr( $settings[ $key ] ) . '"></label>';
    }

    public function frontend_assets() {
        $settings = $this->settings();
        if ( empty( $settings['enabled'] ) ) {
            return;
        }
        wp_enqueue_style( 'ptr-stage14', plugin_dir_url( __FILE__ ) . 'assets/frontend.css', array(), self::VERSION );
        wp_enqueue_script( 'ptr-stage14', plugin_dir_url( __FILE__ ) . 'assets/frontend.js', array(), self::VERSION, true );
        wp_localize_script(
            'ptr-stage14',
            'PTRStage14',
            array(
                'lazyMaps'          => (bool) $settings['lazy_maps'],
                'loadMargin'        => (int) $settings['map_load_margin'],
                'accessibleTables'  => (bool) $settings['accessible_tables'],
                'keyboardMaps'      => (bool) $settings['keyboard_maps'],
                'mobilePageSize'    => (int) $settings['mobile_results_page_size'],
                'desktopPageSize'   => (int) $settings['results_page_size'],
                'mapHeight'         => (int) $settings['map_placeholder_height'],
            )
        );
    }

    public function admin_assets( $hook ) {
        if ( false === strpos( (string) $hook, 'ptr-stage14' ) ) {
            return;
        }
        wp_enqueue_style( 'ptr-stage14-admin', plugin_dir_url( __FILE__ ) . 'assets/admin.css', array(), self::VERSION );
        wp_enqueue_script( 'ptr-stage14-admin', plugin_dir_url( __FILE__ ) . 'assets/admin.js', array( 'jquery' ), self::VERSION, true );
        wp_localize_script(
            'ptr-stage14-admin',
            'PTR14Admin',
            array(
                'ajaxUrl' => admin_url( 'admin-ajax.php' ),
                'nonce'   => wp_create_nonce( self::NONCE ),
            )
        );
    }

    public function render_skip_link() {
        echo '<a class="ptr-skip-link" href="#main">Przejdź do głównej treści</a>';
    }

    public function render_live_region() {
        echo '<div class="ptr-live-region" role="status" aria-live="polite" aria-atomic="true"></div>';
    }

    public function body_classes( $classes ) {
        $classes[] = 'ptr-stage14-active';
        return $classes;
    }

    public function defer_maps_script( $tag, $handle, $src ) {
        $settings = $this->settings();
        if ( empty( $settings['defer_maps'] ) ) {
            return $tag;
        }
        if ( false !== strpos( (string) $src, 'maps.googleapis.com/maps/api/js' ) || false !== strpos( (string) $handle, 'ptr-map' ) ) {
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
        return array_values( array_unique( $urls ) );
    }

    public function clear_cache() {
        check_ajax_referer( self::NONCE, 'nonce' );
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_send_json_error( array( 'message' => 'Brak uprawnień.' ), 403 );
        }
        global $wpdb;
        $transient = $wpdb->esc_like( '_transient_ptr_' ) . '%';
        $timeout   = $wpdb->esc_like( '_transient_timeout_ptr_' ) . '%';
        $deleted   = (int) $wpdb->query(
            $wpdb->prepare(
                "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s OR option_name LIKE %s",
                $transient,
                $timeout
            )
        );
        wp_send_json_success( array( 'message' => sprintf( 'Usunięto %d wpisów cache.', max( 0, $deleted ) ) ) );
    }

    public function test_maps() {
        check_ajax_referer( self::NONCE, 'nonce' );
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_send_json_error( array( 'message' => 'Brak uprawnień.' ), 403 );
        }
        $key    = isset( $_POST['key'] ) ? sanitize_text_field( wp_unslash( $_POST['key'] ) ) : '';
        $map_id = isset( $_POST['map_id'] ) ? sanitize_text_field( wp_unslash( $_POST['map_id'] ) ) : '';
        if ( ! $key ) {
            wp_send_json_error( array( 'message' => 'Wprowadź klucz API.' ) );
        }
        if ( strlen( $key ) < 20 ) {
            wp_send_json_error( array( 'message' => 'Klucz wygląda na niepełny.' ) );
        }
        $message = 'Format klucza jest prawidłowy. Zapisz ustawienia i sprawdź mapę na froncie.';
        if ( ! $map_id ) {
            $message .= ' Map ID jest puste; klasyczna mapa może działać, ale Advanced Markers mogą być niedostępne.';
        }
        wp_send_json_success( array( 'message' => $message ) );
    }

    public function site_health_tests( $tests ) {
        $tests['direct']['ptr_stage14'] = array(
            'label' => 'Przemyśl Tour: Google Maps i WCAG',
            'test'  => array( $this, 'health_test' ),
        );
        return $tests;
    }

    public function health_test() {
        $settings = $this->settings();
        $ok       = ! empty( $settings['google_maps_api_key'] ) && ! empty( $settings['accessible_tables'] );
        return array(
            'label'       => $ok ? 'Konfiguracja Google Maps i WCAG jest aktywna' : 'Konfiguracja Google Maps lub WCAG wymaga uzupełnienia',
            'status'      => $ok ? 'good' : 'recommended',
            'badge'       => array( 'label' => 'Przemyśl Tour', 'color' => 'blue' ),
            'description' => '<p>' . ( $ok ? 'Klucz Google Maps i obsługa dostępnych tabel są skonfigurowane.' : 'Uzupełnij klucz Google Maps i sprawdź ustawienia dostępności.' ) . '</p>',
            'actions'     => '<p><a href="' . esc_url( admin_url( 'admin.php?page=ptr-stage14' ) ) . '">Otwórz ustawienia</a></p>',
            'test'        => 'ptr_stage14',
        );
    }

    public function filter_maps_key( $value ) {
        $settings = $this->settings();
        return ! empty( $settings['google_maps_api_key'] ) ? $settings['google_maps_api_key'] : $value;
    }

    public function filter_map_id( $value ) {
        $settings = $this->settings();
        return ! empty( $settings['google_maps_map_id'] ) ? $settings['google_maps_map_id'] : $value;
    }

    public function filter_results_page_size() {
        $settings = $this->settings();
        return (int) $settings['results_page_size'];
    }

    public function filter_mobile_results_page_size() {
        $settings = $this->settings();
        return (int) $settings['mobile_results_page_size'];
    }

    public function filter_map_point_limit() {
        $settings = $this->settings();
        return (int) $settings['map_point_limit'];
    }

    public function filter_profile_point_limit() {
        $settings = $this->settings();
        return (int) $settings['profile_point_limit'];
    }

    public function filter_cache_ttl() {
        $settings = $this->settings();
        return (int) $settings['cache_minutes'] * MINUTE_IN_SECONDS;
    }

    public static function activate() {
        if ( version_compare( PHP_VERSION, '7.4', '<' ) ) {
            deactivate_plugins( plugin_basename( __FILE__ ) );
            wp_die( 'Przemyśl Tour – Etap 14 wymaga PHP 7.4 lub nowszego.' );
        }
        if ( false === get_option( self::OPTION, false ) ) {
            add_option( self::OPTION, self::defaults(), '', false );
        }
    }
}

register_activation_hook( __FILE__, array( 'PTR_Stage14_Fixed', 'activate' ) );
PTR_Stage14_Fixed::instance();
