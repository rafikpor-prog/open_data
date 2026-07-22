<?php
/**
 * Etap 15 – gotowość produkcyjna, diagnostyka, bezpieczeństwo i dokumentacja.
 *
 * @package PrzemyslTourRaces
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class PTR_Production_Readiness {
    const VERSION       = '1.5.0';
    const DB_VERSION    = '2.3.0';
    const SNAPSHOT      = 'ptr_stage15_readiness_snapshot';
    const CRON_HOOK     = 'ptr_stage15_daily_readiness';
    const NONCE         = 'ptr_stage15_admin_action';
    const RESULT_NOTICE = 'ptr_stage15_admin_notice';

    private static $instance = null;
    private $race_type = 'ptr_race';
    private $route_type = 'ptr_route';

    public static function instance() {
        if ( null === self::$instance ) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        add_action( 'init', array( $this, 'detect_post_types' ), 99 );
        add_action( 'admin_menu', array( $this, 'register_menu' ), 999 );
        add_action( 'admin_enqueue_scripts', array( $this, 'enqueue_admin_assets' ) );
        add_action( 'admin_notices', array( $this, 'show_admin_notice' ) );
        add_action( 'admin_post_ptr_stage15_run_suite', array( $this, 'handle_run_suite' ) );
        add_action( 'admin_post_ptr_stage15_save_settings', array( $this, 'handle_save_settings' ) );
        add_action( 'admin_post_ptr_stage15_export_report', array( $this, 'handle_export_report' ) );
        add_action( 'admin_post_ptr_stage15_test_email', array( $this, 'handle_test_email' ) );
        add_action( 'admin_post_ptr_stage15_clear_cache', array( $this, 'handle_clear_cache' ) );
        add_action( 'template_redirect', array( $this, 'maybe_maintenance_mode' ), 0 );
        add_action( 'send_headers', array( $this, 'security_headers' ) );
        add_filter( 'wp_robots', array( $this, 'maintenance_robots' ) );
        add_filter( 'site_status_tests', array( $this, 'site_health_tests' ) );
        add_action( 'rest_api_init', array( $this, 'register_rest_routes' ) );
        add_action( self::CRON_HOOK, array( $this, 'scheduled_suite' ) );
        add_action( 'admin_init', array( $this, 'maybe_migrate' ) );
    }

    public function detect_post_types() {
        foreach ( array( 'ptr_race', 'ptr_races', 'przemysl_race' ) as $candidate ) {
            if ( post_type_exists( $candidate ) ) {
                $this->race_type = $candidate;
                break;
            }
        }
        foreach ( array( 'ptr_route', 'ptr_routes', 'przemysl_route' ) as $candidate ) {
            if ( post_type_exists( $candidate ) ) {
                $this->route_type = $candidate;
                break;
            }
        }
    }

    public function maybe_migrate() {
        $installed = (string) get_option( 'ptr_db_version', '' );
        if ( version_compare( $installed, self::DB_VERSION, '>=' ) ) {
            if ( ! wp_next_scheduled( self::CRON_HOOK ) ) {
                wp_schedule_event( time() + HOUR_IN_SECONDS, 'daily', self::CRON_HOOK );
            }
            return;
        }
        $settings = $this->settings();
        update_option( 'ptr_settings', $settings, false );
        update_option( 'ptr_db_version', self::DB_VERSION, false );
        update_option( 'ptr_stage15_migrated_at', current_time( 'mysql' ), false );
        if ( ! wp_next_scheduled( self::CRON_HOOK ) ) {
            wp_schedule_event( time() + HOUR_IN_SECONDS, 'daily', self::CRON_HOOK );
        }
        delete_transient( self::SNAPSHOT );
    }

    private function defaults() {
        return array(
            'production_mode' => 0,
            'maintenance_mode' => 0,
            'maintenance_message' => 'Trwają prace serwisowe. Prosimy spróbować ponownie później.',
            'security_headers' => 1,
            'diagnostic_retention_days' => 30,
            'production_contact_email' => get_option( 'admin_email' ),
        );
    }

    private function settings() {
        return wp_parse_args( (array) get_option( 'ptr_settings', array() ), $this->defaults() );
    }

    private function parent_slug() {
        global $menu;
        foreach ( (array) $menu as $entry ) {
            $label = isset( $entry[0] ) ? wp_strip_all_tags( $entry[0] ) : '';
            $slug  = isset( $entry[2] ) ? (string) $entry[2] : '';
            if ( false !== stripos( $label, 'Przemyśl Tour' ) && false === strpos( $slug, 'production-readiness' ) ) {
                return $slug;
            }
        }
        return 'tools.php';
    }

    public function register_menu() {
        add_submenu_page(
            $this->parent_slug(),
            'Gotowość produkcyjna',
            'Gotowość produkcyjna',
            'manage_options',
            'ptr-production-readiness',
            array( $this, 'render_page' )
        );
    }

    public function enqueue_admin_assets( $hook ) {
        if ( false === strpos( (string) $hook, 'ptr-production-readiness' ) ) {
            return;
        }
        wp_enqueue_style( 'ptr-stage15-admin', PTR_PLUGIN_URL . 'assets/css/admin-stage15.css', array(), self::VERSION );
        wp_enqueue_script( 'ptr-stage15-admin', PTR_PLUGIN_URL . 'assets/js/admin-stage15.js', array(), self::VERSION, true );
    }

    private function set_notice( $type, $message ) {
        set_transient(
            self::RESULT_NOTICE . '_' . get_current_user_id(),
            array( 'type' => sanitize_key( $type ), 'message' => sanitize_text_field( $message ) ),
            MINUTE_IN_SECONDS
        );
    }

    public function show_admin_notice() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }
        $notice = get_transient( self::RESULT_NOTICE . '_' . get_current_user_id() );
        if ( ! is_array( $notice ) ) {
            return;
        }
        delete_transient( self::RESULT_NOTICE . '_' . get_current_user_id() );
        $class = 'success' === $notice['type'] ? 'notice-success' : ( 'warning' === $notice['type'] ? 'notice-warning' : 'notice-error' );
        echo '<div class="notice ' . esc_attr( $class ) . ' is-dismissible"><p><strong>Przemyśl Tour:</strong> ' . esc_html( $notice['message'] ) . '</p></div>';
    }

    private function table_exists( $table ) {
        global $wpdb;
        return $table === $wpdb->get_var( $wpdb->prepare( 'SHOW TABLES LIKE %s', $wpdb->esc_like( $table ) ) );
    }

    private function memory_bytes( $value ) {
        $value = trim( (string) $value );
        if ( '' === $value || '-1' === $value ) {
            return PHP_INT_MAX;
        }
        $unit = strtolower( substr( $value, -1 ) );
        $number = (float) $value;
        if ( 'g' === $unit ) {
            $number *= 1024;
        }
        if ( in_array( $unit, array( 'g', 'm' ), true ) ) {
            $number *= 1024;
        }
        if ( in_array( $unit, array( 'g', 'm', 'k' ), true ) ) {
            $number *= 1024;
        }
        return (int) $number;
    }

    private function add_test( &$tests, $id, $label, $ok, $level, $details, $fix = '' ) {
        $tests[] = array(
            'id' => sanitize_key( $id ),
            'label' => (string) $label,
            'status' => $ok ? 'good' : ( 'critical' === $level ? 'critical' : 'recommended' ),
            'details' => (string) $details,
            'fix' => (string) $fix,
        );
    }

    private function maps_key_present() {
        $settings = (array) get_option( 'ptr_settings', array() );
        foreach ( array( 'google_maps_api_key', 'maps_api_key', 'google_api_key' ) as $key ) {
            if ( ! empty( $settings[ $key ] ) ) {
                return true;
            }
        }
        return false;
    }

    private function rest_routes() {
        if ( ! function_exists( 'rest_get_server' ) ) {
            return array();
        }
        return array_keys( rest_get_server()->get_routes() );
    }

    public function run_suite( $force = false ) {
        if ( ! $force ) {
            $cached = get_transient( self::SNAPSHOT );
            if ( is_array( $cached ) ) {
                return $cached;
            }
        }
        global $wpdb;
        $tests = array();
        $upload = wp_upload_dir();
        $settings = $this->settings();
        $routes = $this->rest_routes();
        $reg_table = $wpdb->prefix . 'ptr_registrations';
        $results_table = $wpdb->prefix . 'ptr_results';
        $logs_table = $wpdb->prefix . 'ptr_logs';
        $permalink = (string) get_option( 'permalink_structure' );
        $debug_display = defined( 'WP_DEBUG_DISPLAY' ) && WP_DEBUG_DISPLAY;
        $cron_disabled = defined( 'DISABLE_WP_CRON' ) && DISABLE_WP_CRON;
        $db_charset = strtolower( (string) $wpdb->charset );

        $this->add_test( $tests, 'plugin_version', 'Wersja głównej wtyczki', defined( 'PTR_VERSION' ) && version_compare( PTR_VERSION, self::VERSION, '>=' ), 'critical', defined( 'PTR_VERSION' ) ? 'Wykryto ' . PTR_VERSION : 'Brak stałej PTR_VERSION', 'Wgraj kompletną aktualizację 1.5.0.' );
        $this->add_test( $tests, 'db_version', 'Wersja modelu danych', version_compare( (string) get_option( 'ptr_db_version', '0' ), self::DB_VERSION, '>=' ), 'critical', 'Wersja: ' . (string) get_option( 'ptr_db_version', 'brak' ), 'Otwórz panel administratora ponownie, aby uruchomić migrację.' );
        $this->add_test( $tests, 'wordpress', 'WordPress', version_compare( get_bloginfo( 'version' ), '6.0', '>=' ), 'critical', 'Wersja ' . get_bloginfo( 'version' ), 'Zaktualizuj WordPress.' );
        $this->add_test( $tests, 'php', 'PHP', version_compare( PHP_VERSION, '7.4', '>=' ), 'critical', 'Wersja ' . PHP_VERSION, 'Ustaw PHP 8.1 lub nowszy; minimum techniczne to 7.4.' );
        $this->add_test( $tests, 'memory', 'Limit pamięci PHP', $this->memory_bytes( ini_get( 'memory_limit' ) ) >= 128 * 1024 * 1024, 'recommended', 'Limit ' . ini_get( 'memory_limit' ), 'Zalecane co najmniej 256M przy dużych importach GPX i XLSX.' );
        $this->add_test( $tests, 'https', 'HTTPS', is_ssl(), 'critical', is_ssl() ? 'Połączenie szyfrowane' : 'Strona nie jest obsługiwana przez HTTPS', 'Włącz certyfikat TLS i przekierowanie HTTP → HTTPS.' );
        $this->add_test( $tests, 'permalinks', 'Przyjazne odnośniki', '' !== $permalink, 'critical', '' !== $permalink ? $permalink : 'Tryb prosty', 'Ustaw strukturę nazw wpisów i zapisz bezpośrednie odnośniki.' );
        $this->add_test( $tests, 'uploads', 'Katalog przesyłanych plików', empty( $upload['error'] ) && is_dir( $upload['basedir'] ) && wp_is_writable( $upload['basedir'] ), 'critical', empty( $upload['error'] ) ? $upload['basedir'] : $upload['error'], 'Napraw prawa zapisu katalogu uploads.' );
        $this->add_test( $tests, 'plugin_dir', 'Pliki wtyczki', defined( 'PTR_PLUGIN_DIR' ) && is_dir( PTR_PLUGIN_DIR ) && is_readable( PTR_PLUGIN_DIR ), 'critical', defined( 'PTR_PLUGIN_DIR' ) ? PTR_PLUGIN_DIR : 'Brak PTR_PLUGIN_DIR', 'Sprawdź kompletność paczki aktualizacyjnej.' );
        $this->add_test( $tests, 'simplexml', 'SimpleXML', extension_loaded( 'simplexml' ), 'critical', extension_loaded( 'simplexml' ) ? 'Dostępne' : 'Brak', 'Włącz rozszerzenie PHP SimpleXML.' );
        $this->add_test( $tests, 'json', 'JSON', extension_loaded( 'json' ), 'critical', extension_loaded( 'json' ) ? 'Dostępne' : 'Brak', 'Włącz rozszerzenie PHP JSON.' );
        $this->add_test( $tests, 'mbstring', 'Mbstring', extension_loaded( 'mbstring' ), 'recommended', extension_loaded( 'mbstring' ) ? 'Dostępne' : 'Brak', 'Włącz Mbstring dla poprawnej obsługi polskich znaków.' );
        $this->add_test( $tests, 'registrations_table', 'Tabela uczestników', $this->table_exists( $reg_table ), 'critical', $reg_table, 'Dezaktywuj i ponownie aktywuj wtyczkę na kopii serwisu albo użyj procedury naprawczej.' );
        $this->add_test( $tests, 'results_table', 'Tabela wyników', $this->table_exists( $results_table ), 'critical', $results_table, 'Uruchom migrację Etapu 12 na kopii serwisu.' );
        $this->add_test( $tests, 'logs_table', 'Tabela logów', $this->table_exists( $logs_table ), 'recommended', $logs_table, 'Brak tabeli nie blokuje działania, ale ogranicza historię diagnostyczną.' );
        $this->add_test( $tests, 'race_type', 'Typ treści wyścigu', post_type_exists( $this->race_type ), 'critical', $this->race_type, 'Sprawdź rejestrację typów treści.' );
        $this->add_test( $tests, 'route_type', 'Typ treści trasy', post_type_exists( $this->route_type ), 'critical', $this->route_type, 'Sprawdź rejestrację typów treści.' );
        $this->add_test( $tests, 'rest_races', 'REST API wyścigów', in_array( '/ptr/v1/races', $routes, true ) || $this->route_prefix_exists( $routes, '/ptr/v1/races' ), 'critical', 'Namespace /ptr/v1', 'Odśwież bezpośrednie odnośniki i sprawdź konflikty REST.' );
        $this->add_test( $tests, 'rest_routes', 'REST API tras', in_array( '/ptr/v1/routes', $routes, true ) || $this->route_prefix_exists( $routes, '/ptr/v1/routes' ), 'critical', 'Namespace /ptr/v1', 'Odśwież bezpośrednie odnośniki i sprawdź konflikty REST.' );
        $this->add_test( $tests, 'maps', 'Google Maps API', $this->maps_key_present(), 'recommended', $this->maps_key_present() ? 'Klucz skonfigurowany' : 'Brak klucza', 'Uzupełnij klucz w Przemyśl Tour → Ustawienia.' );
        $this->add_test( $tests, 'cron', 'WP-Cron', ! $cron_disabled, 'recommended', $cron_disabled ? 'DISABLE_WP_CRON = true' : 'Aktywny mechanizm WordPress', 'Skonfiguruj systemowy cron wywołujący wp-cron.php albo włącz WP-Cron.' );
        $this->add_test( $tests, 'stage15_cron', 'Codzienny audyt', (bool) wp_next_scheduled( self::CRON_HOOK ), 'recommended', wp_next_scheduled( self::CRON_HOOK ) ? wp_date( 'd.m.Y H:i', wp_next_scheduled( self::CRON_HOOK ) ) : 'Nie zaplanowano', 'Ponownie otwórz panel albo zapisz ustawienia produkcyjne.' );
        $this->add_test( $tests, 'debug_display', 'Wyświetlanie błędów', ! $debug_display || empty( $settings['production_mode'] ), 'critical', $debug_display ? 'WP_DEBUG_DISPLAY aktywne' : 'Błędy niewidoczne publicznie', 'Na produkcji ustaw WP_DEBUG_DISPLAY na false i loguj błędy poza ekranem.' );
        $this->add_test( $tests, 'admin_email', 'E-mail administratora', is_email( get_option( 'admin_email' ) ), 'critical', get_option( 'admin_email' ), 'Ustaw prawidłowy adres administratora WordPress.' );
        $this->add_test( $tests, 'production_email', 'Kontakt techniczny', is_email( $settings['production_contact_email'] ), 'recommended', $settings['production_contact_email'], 'Uzupełnij kontakt techniczny w ustawieniach Etapu 15.' );
        $this->add_test( $tests, 'db_charset', 'Kodowanie bazy', false !== strpos( $db_charset, 'utf8' ), 'critical', $wpdb->charset . ' / ' . $wpdb->collate, 'Użyj utf8mb4 dla pełnej obsługi polskich znaków.' );
        $this->add_test( $tests, 'security_headers', 'Nagłówki bezpieczeństwa', ! empty( $settings['security_headers'] ), 'recommended', ! empty( $settings['security_headers'] ) ? 'Włączone dla stron Przemyśl Tour' : 'Wyłączone', 'Włącz nagłówki bezpieczeństwa w panelu.' );
        $this->add_test( $tests, 'maintenance_off', 'Tryb konserwacyjny', empty( $settings['maintenance_mode'] ), 'recommended', empty( $settings['maintenance_mode'] ) ? 'Wyłączony' : 'AKTYWNY', 'Wyłącz przed publicznym uruchomieniem serwisu.' );

        $critical = 0;
        $recommended = 0;
        $good = 0;
        foreach ( $tests as $test ) {
            if ( 'critical' === $test['status'] ) {
                $critical++;
            } elseif ( 'recommended' === $test['status'] ) {
                $recommended++;
            } else {
                $good++;
            }
        }
        $total = count( $tests );
        $score = $total ? max( 0, (int) round( 100 * ( $good + 0.5 * $recommended ) / $total ) ) : 0;
        $status = $critical ? 'critical' : ( $recommended ? 'recommended' : 'production' );
        $snapshot = array(
            'generated_at' => current_time( 'mysql' ),
            'generated_at_gmt' => gmdate( 'c' ),
            'score' => $score,
            'status' => $status,
            'summary' => array( 'good' => $good, 'recommended' => $recommended, 'critical' => $critical, 'total' => $total ),
            'tests' => $tests,
            'counts' => $this->safe_counts(),
        );
        set_transient( self::SNAPSHOT, $snapshot, 12 * HOUR_IN_SECONDS );
        update_option( 'ptr_stage15_last_snapshot', $snapshot, false );
        return $snapshot;
    }

    private function route_prefix_exists( $routes, $prefix ) {
        foreach ( $routes as $route ) {
            if ( 0 === strpos( $route, $prefix ) ) {
                return true;
            }
        }
        return false;
    }

    private function safe_counts() {
        global $wpdb;
        $counts = array(
            'races' => post_type_exists( $this->race_type ) ? (int) wp_count_posts( $this->race_type )->publish : 0,
            'routes' => post_type_exists( $this->route_type ) ? (int) wp_count_posts( $this->route_type )->publish : 0,
            'registrations' => 0,
            'results' => 0,
        );
        $reg = $wpdb->prefix . 'ptr_registrations';
        if ( $this->table_exists( $reg ) ) {
            $counts['registrations'] = (int) $wpdb->get_var( 'SELECT COUNT(*) FROM `' . esc_sql( $reg ) . '`' );
        }
        $results = $wpdb->prefix . 'ptr_results';
        if ( $this->table_exists( $results ) ) {
            $counts['results'] = (int) $wpdb->get_var( 'SELECT COUNT(*) FROM `' . esc_sql( $results ) . '`' );
        }
        return $counts;
    }

    public function render_page() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( 'Brak uprawnień.' );
        }
        $snapshot = $this->run_suite();
        $settings = $this->settings();
        $status_labels = array( 'production' => 'Gotowe produkcyjnie', 'recommended' => 'Wymaga dopracowania', 'critical' => 'Nie uruchamiaj produkcyjnie' );
        ?>
        <div class="wrap ptr15-wrap">
            <div class="ptr15-header">
                <div><h1>Gotowość produkcyjna Przemyśl Tour</h1><p>Końcowy audyt Etapu 15, narzędzia operacyjne i dokumentacja stabilnego wydania 1.5.0.</p></div>
                <div class="ptr15-actions"><a class="button" href="<?php echo esc_url( wp_nonce_url( admin_url( 'admin-post.php?action=ptr_stage15_export_report' ), self::NONCE ) ); ?>">Pobierz raport JSON</a><a class="button button-primary" href="<?php echo esc_url( wp_nonce_url( admin_url( 'admin-post.php?action=ptr_stage15_run_suite' ), self::NONCE ) ); ?>">Uruchom pełny test</a></div>
            </div>
            <section class="ptr15-overview ptr15-status--<?php echo esc_attr( $snapshot['status'] ); ?>">
                <div class="ptr15-score" aria-label="Wynik gotowości <?php echo esc_attr( $snapshot['score'] ); ?> procent"><strong><?php echo esc_html( $snapshot['score'] ); ?>%</strong><span>gotowości</span></div>
                <div><h2><?php echo esc_html( $status_labels[ $snapshot['status'] ] ); ?></h2><p>Ostatnia kontrola: <?php echo esc_html( $snapshot['generated_at'] ); ?></p><div class="ptr15-summary"><span><?php echo esc_html( $snapshot['summary']['good'] ); ?> poprawnych</span><span><?php echo esc_html( $snapshot['summary']['recommended'] ); ?> zaleceń</span><span><?php echo esc_html( $snapshot['summary']['critical'] ); ?> krytycznych</span></div></div>
            </section>
            <div class="ptr15-grid">
                <section class="ptr15-panel ptr15-panel--wide">
                    <div class="ptr15-panel__head"><h2>Wyniki kontroli</h2><label>Filtr <select class="ptr15-filter"><option value="all">Wszystkie</option><option value="critical">Krytyczne</option><option value="recommended">Zalecenia</option><option value="good">Poprawne</option></select></label></div>
                    <div class="ptr15-tests">
                    <?php foreach ( $snapshot['tests'] as $test ) : ?>
                        <article class="ptr15-test ptr15-test--<?php echo esc_attr( $test['status'] ); ?>" data-status="<?php echo esc_attr( $test['status'] ); ?>">
                            <span class="dashicons <?php echo 'good' === $test['status'] ? 'dashicons-yes-alt' : 'dashicons-warning'; ?>"></span>
                            <div><h3><?php echo esc_html( $test['label'] ); ?></h3><p><?php echo esc_html( $test['details'] ); ?></p><?php if ( 'good' !== $test['status'] && $test['fix'] ) : ?><p class="ptr15-fix"><strong>Działanie:</strong> <?php echo esc_html( $test['fix'] ); ?></p><?php endif; ?></div>
                        </article>
                    <?php endforeach; ?>
                    </div>
                </section>
                <section class="ptr15-panel">
                    <h2>Tryb produkcyjny</h2>
                    <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
                        <input type="hidden" name="action" value="ptr_stage15_save_settings"><?php wp_nonce_field( self::NONCE ); ?>
                        <label class="ptr15-check"><input type="checkbox" name="production_mode" value="1" <?php checked( ! empty( $settings['production_mode'] ) ); ?>> <span>Włącz tryb produkcyjny</span></label>
                        <label class="ptr15-check"><input type="checkbox" name="security_headers" value="1" <?php checked( ! empty( $settings['security_headers'] ) ); ?>> <span>Dodawaj bezpieczne nagłówki do stron Przemyśl Tour</span></label>
                        <label class="ptr15-field"><span>E-mail techniczny</span><input type="email" name="production_contact_email" value="<?php echo esc_attr( $settings['production_contact_email'] ); ?>"></label>
                        <label class="ptr15-field"><span>Retencja raportów diagnostycznych</span><input type="number" min="1" max="365" name="diagnostic_retention_days" value="<?php echo esc_attr( $settings['diagnostic_retention_days'] ); ?>"> dni</label>
                        <?php submit_button( 'Zapisz ustawienia produkcyjne' ); ?>
                    </form>
                </section>
                <section class="ptr15-panel">
                    <h2>Tryb konserwacyjny</h2>
                    <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
                        <input type="hidden" name="action" value="ptr_stage15_save_settings"><?php wp_nonce_field( self::NONCE ); ?>
                        <input type="hidden" name="production_mode" value="<?php echo empty( $settings['production_mode'] ) ? '0' : '1'; ?>">
                        <input type="hidden" name="security_headers" value="<?php echo empty( $settings['security_headers'] ) ? '0' : '1'; ?>">
                        <input type="hidden" name="production_contact_email" value="<?php echo esc_attr( $settings['production_contact_email'] ); ?>">
                        <input type="hidden" name="diagnostic_retention_days" value="<?php echo esc_attr( $settings['diagnostic_retention_days'] ); ?>">
                        <label class="ptr15-check"><input type="checkbox" name="maintenance_mode" value="1" <?php checked( ! empty( $settings['maintenance_mode'] ) ); ?>> <span>Zablokuj publiczne strony wyścigów i tras</span></label>
                        <label class="ptr15-field"><span>Komunikat</span><textarea name="maintenance_message" rows="4"><?php echo esc_textarea( $settings['maintenance_message'] ); ?></textarea></label>
                        <?php submit_button( 'Zapisz tryb konserwacyjny', 'secondary' ); ?>
                    </form>
                </section>
                <section class="ptr15-panel">
                    <h2>Narzędzia</h2>
                    <p><a class="button" href="<?php echo esc_url( wp_nonce_url( admin_url( 'admin-post.php?action=ptr_stage15_test_email' ), self::NONCE ) ); ?>">Wyślij testowy e-mail</a></p>
                    <p><a class="button" href="<?php echo esc_url( wp_nonce_url( admin_url( 'admin-post.php?action=ptr_stage15_clear_cache' ), self::NONCE ) ); ?>">Wyczyść cache runtime</a></p>
                    <p><a href="<?php echo esc_url( admin_url( 'site-health.php' ) ); ?>">Otwórz Stan witryny WordPress</a></p>
                </section>
                <section class="ptr15-panel">
                    <h2>Dokumentacja</h2>
                    <ul class="ptr15-links"><li><a href="<?php echo esc_url( PTR_PLUGIN_URL . 'docs/ADMINISTRATOR-1.5.0.md' ); ?>" target="_blank" rel="noopener">Podręcznik administratora</a></li><li><a href="<?php echo esc_url( PTR_PLUGIN_URL . 'docs/WERYFIKACJA-PRODUKCYJNA-1.5.0.md' ); ?>" target="_blank" rel="noopener">Checklista wdrożeniowa</a></li><li><a href="<?php echo esc_url( PTR_PLUGIN_URL . 'docs/CHANGELOG-1.5.0.md' ); ?>" target="_blank" rel="noopener">Changelog 1.5.0</a></li></ul>
                </section>
            </div>
        </div>
        <?php
    }

    public function handle_run_suite() {
        $this->guard();
        $snapshot = $this->run_suite( true );
        $this->set_notice( $snapshot['summary']['critical'] ? 'warning' : 'success', 'Pełna kontrola została zakończona. Wynik gotowości: ' . $snapshot['score'] . '%.' );
        $this->redirect();
    }

    public function handle_save_settings() {
        $this->guard();
        $settings = $this->settings();
        $settings['production_mode'] = empty( $_POST['production_mode'] ) ? 0 : 1;
        $settings['maintenance_mode'] = empty( $_POST['maintenance_mode'] ) ? 0 : 1;
        $settings['security_headers'] = empty( $_POST['security_headers'] ) ? 0 : 1;
        $settings['production_contact_email'] = isset( $_POST['production_contact_email'] ) ? sanitize_email( wp_unslash( $_POST['production_contact_email'] ) ) : $settings['production_contact_email'];
        $settings['diagnostic_retention_days'] = isset( $_POST['diagnostic_retention_days'] ) ? min( 365, max( 1, absint( $_POST['diagnostic_retention_days'] ) ) ) : 30;
        $settings['maintenance_message'] = isset( $_POST['maintenance_message'] ) ? sanitize_textarea_field( wp_unslash( $_POST['maintenance_message'] ) ) : $settings['maintenance_message'];
        update_option( 'ptr_settings', $settings, false );
        delete_transient( self::SNAPSHOT );
        $this->set_notice( 'success', 'Ustawienia produkcyjne zostały zapisane.' );
        $this->redirect();
    }

    public function handle_export_report() {
        $this->guard();
        $snapshot = $this->run_suite( true );
        $payload = array(
            'generatedAt' => gmdate( 'c' ),
            'pluginVersion' => defined( 'PTR_VERSION' ) ? PTR_VERSION : '',
            'dataVersion' => (string) get_option( 'ptr_db_version', '' ),
            'wordpress' => get_bloginfo( 'version' ),
            'php' => PHP_VERSION,
            'siteUrl' => home_url( '/' ),
            'locale' => get_locale(),
            'multisite' => is_multisite(),
            'snapshot' => $snapshot,
        );
        nocache_headers();
        header( 'Content-Type: application/json; charset=utf-8' );
        header( 'Content-Disposition: attachment; filename=przemysl-tour-raport-produkcyjny-' . gmdate( 'Y-m-d-His' ) . '.json' );
        echo wp_json_encode( $payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
        exit;
    }

    public function handle_test_email() {
        $this->guard();
        $settings = $this->settings();
        $email = is_email( $settings['production_contact_email'] ) ? $settings['production_contact_email'] : get_option( 'admin_email' );
        $sent = wp_mail( $email, 'Test Przemyśl Tour 1.5.0', 'To jest test wiadomości systemowej modułu gotowości produkcyjnej Przemyśl Tour. Data: ' . current_time( 'mysql' ) );
        $this->set_notice( $sent ? 'success' : 'error', $sent ? 'Wiadomość testowa została przekazana do systemu pocztowego.' : 'WordPress nie potwierdził wysłania wiadomości. Sprawdź SMTP i logi serwera.' );
        $this->redirect();
    }

    public function handle_clear_cache() {
        $this->guard();
        global $wpdb;
        $like_a = $wpdb->esc_like( '_transient_ptr_' ) . '%';
        $like_b = $wpdb->esc_like( '_transient_timeout_ptr_' ) . '%';
        $deleted = (int) $wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s OR option_name LIKE %s", $like_a, $like_b ) );
        delete_transient( self::SNAPSHOT );
        $this->set_notice( 'success', 'Wyczyszczono ' . max( 0, $deleted ) . ' wpisów cache Przemyśl Tour.' );
        $this->redirect();
    }

    private function guard() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( 'Brak uprawnień.' );
        }
        check_admin_referer( self::NONCE );
    }

    private function redirect() {
        wp_safe_redirect( admin_url( 'admin.php?page=ptr-production-readiness' ) );
        exit;
    }

    private function is_ptr_public_request() {
        if ( is_admin() || wp_doing_ajax() || wp_doing_cron() ) {
            return false;
        }
        if ( is_singular( array( $this->race_type, $this->route_type ) ) || is_post_type_archive( array( $this->race_type, $this->route_type ) ) ) {
            return true;
        }
        foreach ( array( 'ptr_route_embed', 'ptr_certificate', 'ptr_registration_manage' ) as $query_var ) {
            if ( get_query_var( $query_var ) ) {
                return true;
            }
        }
        return false;
    }

    public function maybe_maintenance_mode() {
        $settings = $this->settings();
        if ( empty( $settings['maintenance_mode'] ) || current_user_can( 'manage_options' ) || ! $this->is_ptr_public_request() ) {
            return;
        }
        status_header( 503 );
        nocache_headers();
        header( 'Retry-After: 3600' );
        $message = $settings['maintenance_message'];
        ?><!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Przerwa techniczna – <?php echo esc_html( get_bloginfo( 'name' ) ); ?></title><style>body{margin:0;font:18px/1.6 system-ui,sans-serif;background:#f4f6f8;color:#17202a;display:grid;min-height:100vh;place-items:center}.box{max-width:720px;margin:24px;padding:40px;background:#fff;border:1px solid #cfd7df;border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.08)}h1{line-height:1.2}a{color:#005fcc}</style></head><body><main class="box"><h1>Przerwa techniczna</h1><p><?php echo esc_html( $message ); ?></p><p><a href="<?php echo esc_url( home_url( '/' ) ); ?>">Przejdź na stronę główną</a></p></main></body></html><?php
        exit;
    }

    public function maintenance_robots( $robots ) {
        $settings = $this->settings();
        if ( ! empty( $settings['maintenance_mode'] ) && $this->is_ptr_public_request() ) {
            $robots['noindex'] = true;
            $robots['nofollow'] = true;
        }
        return $robots;
    }

    public function security_headers() {
        $settings = $this->settings();
        if ( empty( $settings['security_headers'] ) || headers_sent() || ! $this->is_ptr_public_request() ) {
            return;
        }
        header( 'X-Content-Type-Options: nosniff' );
        header( 'Referrer-Policy: strict-origin-when-cross-origin' );
        header( 'Permissions-Policy: camera=(), microphone=(), geolocation=(self)' );
        header( 'X-Frame-Options: SAMEORIGIN' );
    }

    public function scheduled_suite() {
        $this->run_suite( true );
        $this->cleanup_old_snapshots();
    }

    private function cleanup_old_snapshots() {
        $settings = $this->settings();
        $days = max( 1, (int) $settings['diagnostic_retention_days'] );
        $last = get_option( 'ptr_stage15_last_snapshot' );
        if ( is_array( $last ) && ! empty( $last['generated_at_gmt'] ) && strtotime( $last['generated_at_gmt'] ) < time() - $days * DAY_IN_SECONDS ) {
            delete_option( 'ptr_stage15_last_snapshot' );
        }
    }

    public function site_health_tests( $tests ) {
        $tests['direct']['ptr_stage15_readiness'] = array(
            'label' => 'Przemyśl Tour: gotowość produkcyjna',
            'test' => array( $this, 'site_health_result' ),
        );
        return $tests;
    }

    public function site_health_result() {
        $snapshot = $this->run_suite();
        $ok = 0 === (int) $snapshot['summary']['critical'];
        return array(
            'label' => $ok ? 'Przemyśl Tour nie ma krytycznych błędów gotowości' : 'Przemyśl Tour ma krytyczne problemy gotowości',
            'status' => $ok ? 'good' : 'critical',
            'badge' => array( 'label' => 'Przemyśl Tour', 'color' => 'blue' ),
            'description' => '<p>Wynik gotowości: <strong>' . esc_html( $snapshot['score'] ) . '%</strong>. Krytyczne: ' . esc_html( $snapshot['summary']['critical'] ) . ', zalecenia: ' . esc_html( $snapshot['summary']['recommended'] ) . '.</p>',
            'actions' => '<p><a href="' . esc_url( admin_url( 'admin.php?page=ptr-production-readiness' ) ) . '">Otwórz pełny raport</a></p>',
            'test' => 'ptr_stage15_readiness',
        );
    }

    public function register_rest_routes() {
        register_rest_route(
            'ptr/v1',
            '/system/health',
            array(
                'methods' => WP_REST_Server::READABLE,
                'callback' => function () {
                    return rest_ensure_response( $this->run_suite() );
                },
                'permission_callback' => function () {
                    return current_user_can( 'manage_options' );
                },
            )
        );
    }
}

PTR_Production_Readiness::instance();
