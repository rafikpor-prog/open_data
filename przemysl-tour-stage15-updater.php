<?php
/**
 * Plugin Name: Przemyśl Tour – Aktualizator Etapu 15
 * Description: Jednorazowy instalator aktualizacji głównej wtyczki Przemyśl Tour – Wyścigi i Trasy z wersji 1.4.0 do stabilnej wersji 1.5.0.
 * Version: 1.0.0
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * Author: Fundacja Sportowa Przemyśl Tour
 * Text Domain: ptr-stage15-updater
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class PTR_Stage15_Updater {
    const TARGET_PLUGIN = 'przemysl-tour-races/przemysl-tour-races.php';
    const TARGET_DIR    = 'przemysl-tour-races';
    const NONCE_ACTION  = 'ptr_stage15_apply_update';
    const RESULT_KEY    = 'ptr_stage15_updater_result';

    private static $instance = null;

    public static function instance() {
        if ( null === self::$instance ) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        add_action( 'admin_menu', array( $this, 'register_page' ) );
        add_action( 'admin_post_ptr_stage15_apply_update', array( $this, 'apply_update' ) );
        add_action( 'admin_notices', array( $this, 'admin_notice' ) );
        add_filter( 'plugin_action_links_' . plugin_basename( __FILE__ ), array( $this, 'action_links' ) );
    }

    public function action_links( $links ) {
        array_unshift( $links, '<a href="' . esc_url( admin_url( 'tools.php?page=ptr-stage15-updater' ) ) . '">Uruchom aktualizację</a>' );
        return $links;
    }

    public function register_page() {
        add_management_page(
            'Aktualizacja Przemyśl Tour 1.5.0',
            'Aktualizacja Przemyśl Tour',
            'update_plugins',
            'ptr-stage15-updater',
            array( $this, 'render_page' )
        );
    }

    private function target_path() {
        return trailingslashit( WP_PLUGIN_DIR ) . self::TARGET_PLUGIN;
    }

    private function target_dir() {
        return trailingslashit( WP_PLUGIN_DIR ) . self::TARGET_DIR;
    }

    private function detect_version() {
        $file = $this->target_path();
        if ( ! is_readable( $file ) ) {
            return '';
        }
        if ( ! function_exists( 'get_file_data' ) ) {
            require_once ABSPATH . 'wp-admin/includes/plugin.php';
        }
        $data = get_file_data( $file, array( 'Version' => 'Version' ), 'plugin' );
        return isset( $data['Version'] ) ? (string) $data['Version'] : '';
    }

    private function preflight() {
        $target = $this->target_path();
        $dir    = $this->target_dir();
        $version = $this->detect_version();
        $checks = array(
            'php' => array( version_compare( PHP_VERSION, '7.4', '>=' ), 'PHP 7.4 lub nowszy' ),
            'wordpress' => array( version_compare( get_bloginfo( 'version' ), '6.0', '>=' ), 'WordPress 6.0 lub nowszy' ),
            'target' => array( is_file( $target ), 'Istniejąca główna wtyczka przemysl-tour-races' ),
            'version' => array( version_compare( $version, '1.4.0', '>=' ) && version_compare( $version, '1.5.0', '<' ), 'Wersja źródłowa od 1.4.0 do 1.4.x' ),
            'writable' => array( is_dir( $dir ) && wp_is_writable( $dir ), 'Możliwość zapisu w katalogu głównej wtyczki' ),
            'payload' => array( is_dir( plugin_dir_path( __FILE__ ) . 'payload' ), 'Kompletny pakiet aktualizacyjny' ),
        );
        return array( 'version' => $version, 'checks' => $checks );
    }

    public function render_page() {
        if ( ! current_user_can( 'update_plugins' ) ) {
            wp_die( 'Brak uprawnień.' );
        }
        $preflight = $this->preflight();
        $ready = true;
        foreach ( $preflight['checks'] as $check ) {
            if ( ! $check[0] ) {
                $ready = false;
            }
        }
        ?>
        <div class="wrap">
            <h1>Aktualizacja Przemyśl Tour do wersji 1.5.0</h1>
            <p>Ten instalator <strong>nie tworzy drugiej wersji wtyczki</strong>. Kopiuje pliki Etapu 15 bezpośrednio do istniejącego katalogu <code>przemysl-tour-races</code>, aktualizuje główny plik i zachowuje wszystkie dane.</p>
            <div class="card" style="max-width:900px;padding:20px">
                <h2>Kontrola przed aktualizacją</h2>
                <table class="widefat striped"><tbody>
                <?php foreach ( $preflight['checks'] as $check ) : ?>
                    <tr><td style="width:44px"><span class="dashicons <?php echo $check[0] ? 'dashicons-yes-alt' : 'dashicons-warning'; ?>" style="color:<?php echo $check[0] ? '#008a20' : '#b32d2e'; ?>"></span></td><td><?php echo esc_html( $check[1] ); ?></td><td><strong><?php echo $check[0] ? 'OK' : 'BŁĄD'; ?></strong></td></tr>
                <?php endforeach; ?>
                </tbody></table>
                <p>Wykryta wersja głównej wtyczki: <strong><?php echo esc_html( $preflight['version'] ? $preflight['version'] : 'nie wykryto' ); ?></strong></p>
                <?php if ( $ready ) : ?>
                    <form action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" method="post">
                        <input type="hidden" name="action" value="ptr_stage15_apply_update">
                        <?php wp_nonce_field( self::NONCE_ACTION ); ?>
                        <p><label><input type="checkbox" required> Potwierdzam, że wykonano kopię zapasową strony i bazy danych.</label></p>
                        <?php submit_button( 'Zainstaluj Etap 15 i zaktualizuj do 1.5.0', 'primary large' ); ?>
                    </form>
                <?php else : ?>
                    <div class="notice notice-error inline"><p>Aktualizacja nie może zostać wykonana. Usuń wskazane błędy i ponownie otwórz tę stronę.</p></div>
                <?php endif; ?>
            </div>
            <p><strong>Po poprawnej aktualizacji:</strong> przejdź do <em>Przemyśl Tour → Gotowość produkcyjna</em>, uruchom pełny test, a następnie usuń ten jednorazowy aktualizator.</p>
        </div>
        <?php
    }

    public function admin_notice() {
        if ( ! current_user_can( 'update_plugins' ) ) {
            return;
        }
        $result = get_transient( self::RESULT_KEY . '_' . get_current_user_id() );
        if ( ! is_array( $result ) ) {
            return;
        }
        delete_transient( self::RESULT_KEY . '_' . get_current_user_id() );
        $class = ! empty( $result['success'] ) ? 'notice notice-success' : 'notice notice-error';
        echo '<div class="' . esc_attr( $class ) . ' is-dismissible"><p><strong>Przemyśl Tour:</strong> ' . esc_html( $result['message'] ) . '</p></div>';
    }

    private function recursive_copy( $source, $destination ) {
        if ( ! is_dir( $source ) ) {
            return false;
        }
        if ( ! is_dir( $destination ) && ! wp_mkdir_p( $destination ) ) {
            return false;
        }
        $iterator = new RecursiveIteratorIterator(
            new RecursiveDirectoryIterator( $source, FilesystemIterator::SKIP_DOTS ),
            RecursiveIteratorIterator::SELF_FIRST
        );
        foreach ( $iterator as $item ) {
            $relative = substr( $item->getPathname(), strlen( $source ) + 1 );
            $target   = trailingslashit( $destination ) . $relative;
            if ( $item->isDir() ) {
                if ( ! is_dir( $target ) && ! wp_mkdir_p( $target ) ) {
                    return false;
                }
            } else {
                if ( ! is_dir( dirname( $target ) ) && ! wp_mkdir_p( dirname( $target ) ) ) {
                    return false;
                }
                if ( ! copy( $item->getPathname(), $target ) ) {
                    return false;
                }
                @chmod( $target, 0644 );
            }
        }
        return true;
    }

    private function patch_main_file( $file ) {
        $source = file_get_contents( $file );
        if ( false === $source ) {
            return new WP_Error( 'read_failed', 'Nie można odczytać głównego pliku wtyczki.' );
        }
        $original = $source;
        $source = preg_replace( '/(^\s*\*\s*Version:\s*)1\.4\.[0-9]+/mi', '${1}1.5.0', $source, 1 );
        $source = preg_replace( "/define\(\s*'PTR_VERSION'\s*,\s*'1\.4\.[0-9]+'\s*\);/", "define( 'PTR_VERSION', '1.5.0' );", $source, 1 );
        $source = preg_replace( "/define\(\s*'PTR_DB_VERSION'\s*,\s*'2\.2\.[0-9]+'\s*\);/", "define( 'PTR_DB_VERSION', '2.3.0' );", $source, 1 );

        $include = "require_once PTR_PLUGIN_DIR . 'includes/class-ptr-production-readiness.php';";
        if ( false === strpos( $source, 'class-ptr-production-readiness.php' ) ) {
            $anchors = array( 'PTR_Plugin::instance();', 'PTR_Core::instance();' );
            $inserted = false;
            foreach ( $anchors as $anchor ) {
                $position = strrpos( $source, $anchor );
                if ( false !== $position ) {
                    $source = substr( $source, 0, $position ) . $include . "\n" . substr( $source, $position );
                    $inserted = true;
                    break;
                }
            }
            if ( ! $inserted ) {
                $source = preg_replace( '/\?>\s*$/', '', $source ) . "\n" . $include . "\n";
            }
        }
        if ( $source === $original || false === strpos( $source, "PTR_VERSION', '1.5.0" ) || false === strpos( $source, 'class-ptr-production-readiness.php' ) ) {
            return new WP_Error( 'patch_failed', 'Nie udało się bezpiecznie zmienić wersji lub dodać modułu produkcyjnego.' );
        }
        $temp = $file . '.stage15.tmp';
        if ( false === file_put_contents( $temp, $source, LOCK_EX ) ) {
            return new WP_Error( 'write_failed', 'Nie można zapisać tymczasowego pliku głównego.' );
        }
        if ( ! rename( $temp, $file ) ) {
            @unlink( $temp );
            return new WP_Error( 'replace_failed', 'Nie można podmienić głównego pliku wtyczki.' );
        }
        @chmod( $file, 0644 );
        return true;
    }

    public function apply_update() {
        if ( ! current_user_can( 'update_plugins' ) ) {
            wp_die( 'Brak uprawnień.' );
        }
        check_admin_referer( self::NONCE_ACTION );
        $preflight = $this->preflight();
        foreach ( $preflight['checks'] as $check ) {
            if ( ! $check[0] ) {
                $this->redirect_result( false, 'Aktualizacja przerwana, ponieważ kontrola wstępna wykazała błąd.' );
            }
        }

        $target_dir  = $this->target_dir();
        $target_file = $this->target_path();
        $upload      = wp_upload_dir();
        $backup_dir  = trailingslashit( $upload['basedir'] ) . 'ptr-backups/stage15-' . gmdate( 'Ymd-His' );
        if ( ! empty( $upload['error'] ) || ! wp_mkdir_p( $backup_dir ) ) {
            $this->redirect_result( false, 'Nie można utworzyć katalogu kopii bezpieczeństwa w uploads.' );
        }
        if ( ! $this->recursive_copy( $target_dir, $backup_dir . '/przemysl-tour-races' ) ) {
            $this->redirect_result( false, 'Nie udało się utworzyć kopii bezpieczeństwa katalogu wtyczki.' );
        }

        $payload = plugin_dir_path( __FILE__ ) . 'payload';
        if ( ! $this->recursive_copy( $payload, $target_dir ) ) {
            $this->redirect_result( false, 'Nie udało się skopiować plików Etapu 15. Kopia bezpieczeństwa pozostała w: ' . $backup_dir );
        }
        $patched = $this->patch_main_file( $target_file );
        if ( is_wp_error( $patched ) ) {
            @copy( $backup_dir . '/przemysl-tour-races/przemysl-tour-races.php', $target_file );
            $this->redirect_result( false, $patched->get_error_message() . ' Przywrócono główny plik z kopii.' );
        }

        $settings = (array) get_option( 'ptr_settings', array() );
        $settings = wp_parse_args(
            $settings,
            array(
                'production_mode' => 0,
                'maintenance_mode' => 0,
                'maintenance_message' => 'Trwają prace serwisowe. Prosimy spróbować ponownie później.',
                'security_headers' => 1,
                'diagnostic_retention_days' => 30,
                'production_contact_email' => get_option( 'admin_email' ),
            )
        );
        update_option( 'ptr_settings', $settings, false );
        update_option( 'ptr_db_version', '2.3.0', false );
        update_option( 'ptr_stage15_installed', array( 'version' => '1.5.0', 'installed_at' => current_time( 'mysql' ), 'backup_dir' => $backup_dir ), false );
        delete_transient( 'ptr_stage15_readiness_snapshot' );
        if ( function_exists( 'opcache_reset' ) ) {
            @opcache_reset();
        }
        $this->redirect_result( true, 'Aktualizacja do wersji 1.5.0 została wykonana. Kopia plików znajduje się w ' . $backup_dir . '. Otwórz teraz Przemyśl Tour → Gotowość produkcyjna.' );
    }

    private function redirect_result( $success, $message ) {
        set_transient(
            self::RESULT_KEY . '_' . get_current_user_id(),
            array( 'success' => (bool) $success, 'message' => (string) $message ),
            MINUTE_IN_SECONDS
        );
        $url = $success ? admin_url( 'admin.php?page=ptr-production-readiness' ) : admin_url( 'tools.php?page=ptr-stage15-updater' );
        wp_safe_redirect( $url );
        exit;
    }
}

PTR_Stage15_Updater::instance();
