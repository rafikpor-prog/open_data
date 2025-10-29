<?php
/**
 * Plugin Name:       Open Data Plugin Bridge
 * Plugin URI:        https://example.com/open-data-plugin
 * Description:       Integracja wtyczki Open Data z WordPressem – panel administracyjny, shortcody i synchronizacja z usługami API.
 * Version:           0.1.0
 * Author:            Open Data Team
 * License:           GPL-3.0-or-later
 * Text Domain:       open-data-plugin
 *
 * Ten plik implementuje pełną wtyczkę WordPress, która wykorzystuje WordPress jako
 * bazowy system CMS do zarządzania danymi, wizualizacjami i publikacją katalogu.
 * Kluczowe elementy:
 * - klasa Open_Data_Plugin: singleton inicjujący rejestrację CPT, ustawień i hooków,
 * - panel administracyjny Studio Danych (ustawienia API, ręczna synchronizacja),
 * - shortcode `[open_data_dataset]` renderujący dane pobrane przez REST API,
 * - wykorzystanie cron/akcji do synchronizacji z mikroserwisem ingestion/visualization,
 * - pełna integracja z kontraktami API opisanymi w README (REST/JSON:API, OAuth 2.0).
 */

if (!defined('ABSPATH')) {
    exit;
}

if (!class_exists('Open_Data_Plugin')) {
    /**
     * Class Open_Data_Plugin
     * Technical description:
     *     Główny singleton uruchamiający wtyczkę. Rejestruje typ wpisu
     *     `open_data_dataset`, hooki administracyjne, shortcody oraz harmonogram
     *     synchronizacji danych z backendem Python (ingestion-service,
     *     visualization-service).
     *
     * Instructions for laika:
     *     "To serce wtyczki – dba o to, by WordPress znał nowe typy wpisów, miał
     *     formularz ustawień i potrafił pobierać dane z serwera Open Data." 
     *
     * Example:
     *     ```php
     *     Open_Data_Plugin::instance();
     *     ```
     * Effect for end user:
     *     Administrator WordPress otrzymuje panel Studio Danych, możliwość
     *     synchronizacji katalogu i publikacji wizualizacji zgodnych z
     *     dane.gov.pl oraz API BDL bez opuszczania WordPressa.
     */
    final class Open_Data_Plugin {
        /** @var Open_Data_Plugin|null */
        private static $instance = null;

        /**
         * Zwraca jedyną instancję klasy.
         * Technical description:
         *     Singleton – jeśli instancja nie istnieje, tworzy ją i rejestruje
         *     wszystkie hooki w WordPress.
         * Instructions for laika:
         *     "Pierwsze wywołanie uruchamia wtyczkę i podłącza ją do WordPressa." 
         * Example:
         *     `Open_Data_Plugin::instance();`
         * Effect for end user:
         *     Zapewnia, że wtyczka działa spójnie niezależnie od liczby wywołań.
         *
         * @return Open_Data_Plugin
         */
        public static function instance() {
            if (self::$instance === null) {
                self::$instance = new self();
                self::$instance->hooks();
            }
            return self::$instance;
        }

        /**
         * Rejestruje wszystkie hooki WordPress.
         * Technical description:
         *     Dodaje akcje `init`, `admin_menu`, `admin_post_odp_sync_now`,
         *     `admin_init` (rejestracja ustawień), shortcode oraz harmonogram cron.
         * Instructions for laika:
         *     "Podpinamy wtyczkę w odpowiednich miejscach WordPressa: dodajemy
         *     nowe menu, formularze i zadania automatyczne."
         * Example:
         *     `Open_Data_Plugin::instance()->hooks();`
         * Effect for end user:
         *     Umożliwia konfigurację i automatyczną synchronizację danych w WordPress.
         */
        public function hooks(): void {
            add_action('init', [$this, 'register_post_type']);
            add_action('init', [$this, 'register_cron_schedule']);
            add_action('admin_menu', [$this, 'register_admin_menu']);
            add_action('admin_init', [$this, 'register_settings']);
            add_action('admin_post_odp_sync_now', [$this, 'handle_manual_sync']);
            add_shortcode('open_data_dataset', [$this, 'render_dataset_shortcode']);
            add_action('odp_sync_event', [$this, 'synchronize_datasets']);
        }

        /**
         * Rejestruje harmonogram synchronizacji (co 12 godzin).
         * Technical description:
         *     Dodaje własny harmonogram `odp_twice_daily` (co 12 godzin) oraz
         *     zapewnia, że zdarzenie `odp_sync_event` jest zaplanowane.
         * Instructions for laika:
         *     "WordPress automatycznie odświeża dane dwa razy dziennie." 
         * Example:
         *     Automatycznie wywoływane przez `hooks()`.
         * Effect for end user:
         *     Dane w katalogu są aktualne bez ręcznego pobierania plików.
         */
        public function register_cron_schedule(): void {
            add_filter('cron_schedules', static function (array $schedules): array {
                if (!isset($schedules['odp_twice_daily'])) {
                    $schedules['odp_twice_daily'] = [
                        'interval' => 12 * HOUR_IN_SECONDS,
                        'display' => __('Co 12 godzin (Open Data)', 'open-data-plugin'),
                    ];
                }
                return $schedules;
            });

            if (!wp_next_scheduled('odp_sync_event')) {
                wp_schedule_event(time() + HOUR_IN_SECONDS, 'odp_twice_daily', 'odp_sync_event');
            }
        }

        /**
         * Rejestruje niestandardowy typ wpisu.
         * Technical description:
         *     Tworzy typ `open_data_dataset` wykorzystywany do przechowywania
         *     opisów zbiorów i wizualizacji pobranych z backendu.
         * Instructions for laika:
         *     "W WordPressie pojawi się nowa sekcja 'Zbiory danych' z wpisami
         *     reprezentującymi katalog danych i raporty." 
         * Example:
         *     Automatycznie podczas `init`.
         * Effect for end user:
         *     Zbiory danych są dostępne w panelu WordPress i mogą być
         *     publikowane jak standardowe wpisy/strony.
         */
        public function register_post_type(): void {
            register_post_type('open_data_dataset', [
                'labels' => [
                    'name' => __('Zbiory danych', 'open-data-plugin'),
                    'singular_name' => __('Zbiór danych', 'open-data-plugin'),
                ],
                'public' => true,
                'has_archive' => true,
                'show_in_rest' => true,
                'supports' => ['title', 'editor', 'custom-fields'],
            ]);
        }

        /**
         * Rejestruje sekcję menu administracyjnego.
         * Technical description:
         *     Dodaje pozycję "Studio Danych" w menu administratora z formularzem
         *     konfiguracji i przyciskiem ręcznej synchronizacji.
         * Instructions for laika:
         *     "W menu pojawi się zakładka, w której ustawisz adres API i wciśniesz
         *     przycisk 'Synchronizuj teraz'."
         * Example:
         *     Automatycznie w panelu administratora.
         * Effect for end user:
         *     Ułatwia konfigurację i manualne odświeżanie danych bez znajomości API.
         */
        public function register_admin_menu(): void {
            add_menu_page(
                __('Studio Danych', 'open-data-plugin'),
                __('Studio Danych', 'open-data-plugin'),
                'manage_options',
                'open-data-studio',
                [$this, 'render_admin_page'],
                'dashicons-database-view',
                56
            );
        }

        /**
         * Rejestruje ustawienia w Options API.
         * Technical description:
         *     Definiuje opcje: `odp_api_base`, `odp_api_token`, `odp_default_profile`.
         * Instructions for laika:
         *     "Zapamiętujemy w WordPressie adres serwera danych, klucz API i domyślny profil." 
         * Example:
         *     Automatycznie podczas `admin_init`.
         * Effect for end user:
         *     Nie trzeba ponownie wpisywać konfiguracji przy każdym logowaniu.
         */
        public function register_settings(): void {
            register_setting('open-data-settings', 'odp_api_base');
            register_setting('open-data-settings', 'odp_api_token');
            register_setting('open-data-settings', 'odp_default_profile');
        }

        /**
         * Renderuje stronę ustawień w panelu administratora.
         * Technical description:
         *     Wyświetla formularz konfiguracji oraz tabelę z ostatnimi wpisami
         *     typu `open_data_dataset`. Formularz wysyła dane do `admin-post.php`
         *     w celu wyzwolenia synchronizacji.
         * Instructions for laika:
         *     "Tu wpisujesz adres API, klucz dostępu i możesz jednym kliknięciem
         *     pobrać aktualne dane z serwera." 
         * Example:
         *     Automatyczne renderowanie w menu "Studio Danych".
         * Effect for end user:
         *     Intuicyjny panel pozwala skonfigurować połączenie z pluginem Python
         *     bez ingerencji w kod.
         */
        public function render_admin_page(): void {
            if (!current_user_can('manage_options')) {
                wp_die(__('Nie masz uprawnień do tej sekcji.', 'open-data-plugin'));
            }
            $api_base = esc_attr(get_option('odp_api_base', 'http://localhost:8000'));
            $api_token = esc_attr(get_option('odp_api_token', ''));
            $profile = esc_attr(get_option('odp_default_profile', 'dev'));
            $datasets = get_posts([
                'post_type' => 'open_data_dataset',
                'posts_per_page' => 10,
                'post_status' => 'publish',
            ]);
            ?>
            <div class="wrap">
                <h1><?php esc_html_e('Studio Danych – konfiguracja', 'open-data-plugin'); ?></h1>
                <form method="post" action="options.php">
                    <?php settings_fields('open-data-settings'); ?>
                    <table class="form-table" role="presentation">
                        <tr>
                            <th scope="row"><?php esc_html_e('Adres API (admin-gateway)', 'open-data-plugin'); ?></th>
                            <td><input type="url" name="odp_api_base" value="<?php echo $api_base; ?>" class="regular-text" required></td>
                        </tr>
                        <tr>
                            <th scope="row"><?php esc_html_e('Token OAuth 2.0', 'open-data-plugin'); ?></th>
                            <td><input type="text" name="odp_api_token" value="<?php echo $api_token; ?>" class="regular-text" placeholder="Bearer ..."></td>
                        </tr>
                        <tr>
                            <th scope="row"><?php esc_html_e('Domyślny profil konfiguracji', 'open-data-plugin'); ?></th>
                            <td><input type="text" name="odp_default_profile" value="<?php echo $profile; ?>" class="regular-text"></td>
                        </tr>
                    </table>
                    <?php submit_button(__('Zapisz ustawienia', 'open-data-plugin')); ?>
                </form>

                <form method="post" action="<?php echo esc_url(admin_url('admin-post.php')); ?>">
                    <?php wp_nonce_field('odp_sync_now', 'odp_sync_nonce'); ?>
                    <input type="hidden" name="action" value="odp_sync_now">
                    <?php submit_button(__('Synchronizuj teraz', 'open-data-plugin'), 'secondary'); ?>
                </form>

                <h2><?php esc_html_e('Ostatnio zaktualizowane zbiory', 'open-data-plugin'); ?></h2>
                <table class="widefat">
                    <thead>
                    <tr>
                        <th><?php esc_html_e('Tytuł', 'open-data-plugin'); ?></th>
                        <th><?php esc_html_e('Data aktualizacji', 'open-data-plugin'); ?></th>
                    </tr>
                    </thead>
                    <tbody>
                    <?php foreach ($datasets as $dataset) : ?>
                        <tr>
                            <td><a href="<?php echo esc_url(get_edit_post_link($dataset->ID)); ?>"><?php echo esc_html($dataset->post_title); ?></a></td>
                            <td><?php echo esc_html(get_date_from_gmt($dataset->post_modified_gmt)); ?></td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
            <?php
        }

        /**
         * Obsługuje ręczną synchronizację.
         * Technical description:
         *     Waliduje nonce, uruchamia `synchronize_datasets()` i przekierowuje
         *     z komunikatem o powodzeniu/niepowodzeniu.
         * Instructions for laika:
         *     "Po kliknięciu przycisku pobieramy dane i wracamy na stronę z informacją o wyniku." 
         * Example:
         *     Automatycznie wywoływane przez WordPress.
         * Effect for end user:
         *     Pozwala natychmiast zaktualizować katalog bez czekania na cron.
         */
        public function handle_manual_sync(): void {
            if (!current_user_can('manage_options')) {
                wp_die(__('Brak uprawnień do synchronizacji.', 'open-data-plugin'));
            }
            check_admin_referer('odp_sync_now', 'odp_sync_nonce');
            $result = $this->synchronize_datasets();
            $redirect = add_query_arg('odp_sync', $result ? 'success' : 'error', admin_url('admin.php?page=open-data-studio'));
            wp_safe_redirect($redirect);
            exit;
        }

        /**
         * Wykonuje synchronizację danych z API.
         * Technical description:
         *     Pobiera listę zbiorów (`GET /datasets`) i dla każdego tworzy/aktualizuje
         *     wpis WordPress wraz z metadanymi (licencja, słowa kluczowe, link JSON-LD).
         *     Wykorzystuje token OAuth (jeśli ustawiony) oraz cache transjentów,
         *     aby ograniczyć liczbę zapytań.
         * Instructions for laika:
         *     "Łączymy się z serwerem danych i tworzymy/aktualizujemy wpisy w WordPressie,
         *     łącznie z licencją i linkiem do pliku JSON-LD." 
         * Example:
         *     `Open_Data_Plugin::instance()->synchronize_datasets();`
         * Effect for end user:
         *     Katalog danych w WordPressie jest zgodny z backendem Open Data,
         *     zawiera licencje i słowa kluczowe z DCAT-AP, a wizualizacje są
         *     dostępne w postaci wpisów i shortcode'ów.
         *
         * @return bool
         */
        public function synchronize_datasets(): bool {
            $api_base = rtrim(get_option('odp_api_base', ''), '/');
            if (empty($api_base)) {
                return false;
            }
            $datasets = $this->fetch_from_api('/datasets');
            if (!is_array($datasets)) {
                return false;
            }
            foreach ($datasets as $dataset) {
                $title = isset($dataset['title']) ? sanitize_text_field($dataset['title']) : __('Zbiór danych', 'open-data-plugin');
                $content = isset($dataset['description']) ? wp_kses_post($dataset['description']) : '';
                $slug = sanitize_title($title . '-' . ($dataset['id'] ?? wp_generate_uuid4()));
                $existing = get_page_by_path($slug, OBJECT, 'open_data_dataset');
                $post_data = [
                    'post_title' => $title,
                    'post_name' => $slug,
                    'post_content' => $content,
                    'post_type' => 'open_data_dataset',
                    'post_status' => 'publish',
                ];
                if ($existing) {
                    $post_data['ID'] = $existing->ID;
                    $post_id = wp_update_post($post_data);
                } else {
                    $post_id = wp_insert_post($post_data);
                }

                if (!is_wp_error($post_id)) {
                    if (isset($dataset['license'])) {
                        update_post_meta($post_id, '_odp_license', sanitize_text_field($dataset['license']));
                    }
                    if (!empty($dataset['keywords']) && is_array($dataset['keywords'])) {
                        $keywords = array_map('sanitize_text_field', (array) $dataset['keywords']);
                        update_post_meta($post_id, '_odp_keywords', $keywords);
                    }
                    if (isset($dataset['accrual_periodicity'])) {
                        update_post_meta($post_id, '_odp_accrual', sanitize_text_field($dataset['accrual_periodicity']));
                    }
                    if (!empty($dataset['jsonld_path'])) {
                        update_post_meta($post_id, '_odp_jsonld', esc_url_raw($dataset['jsonld_path']));
                    } elseif (!empty($dataset['links']['jsonld'])) {
                        update_post_meta($post_id, '_odp_jsonld', esc_url_raw($dataset['links']['jsonld']));
                    }
                }
            }
            return true;
        }

        /**
         * Renderuje shortcode `[open_data_dataset id="..."]`.
         * Technical description:
         *     Pobiera dane z endpointu `GET /datasets/{id}` i wizualizacje
         *     (`GET /visualizations?dataset_id=`). Wynik renderuje w formie tabeli
         *     i listy plików do pobrania.
         * Instructions for laika:
         *     "Wstaw shortcode na stronie, aby pokazać dane wraz z wykresami i
         *     przyciskiem pobrania." 
         * Example:
         *     `[open_data_dataset id="population"]`
         * Effect for end user:
         *     Użytkownicy portalu widzą aktualne dane i wykresy wprost na stronie WordPress.
         *
         * @param array<string,string> $atts
         * @return string
         */
        public function render_dataset_shortcode(array $atts): string {
            $atts = shortcode_atts([
                'id' => '',
            ], $atts);
            $dataset_id = sanitize_text_field($atts['id']);
            if (empty($dataset_id)) {
                return '<p>' . esc_html__('Nie podano identyfikatora zbioru.', 'open-data-plugin') . '</p>';
            }
            $dataset = $this->fetch_from_api('/datasets/' . rawurlencode($dataset_id));
            if (!is_array($dataset)) {
                return '<p>' . esc_html__('Nie udało się pobrać danych.', 'open-data-plugin') . '</p>';
            }
            $visualizations = $this->fetch_from_api('/visualizations?dataset_id=' . rawurlencode($dataset_id));
            $output = '<div class="open-data-dataset">';
            $output .= '<h2>' . esc_html($dataset['title'] ?? $dataset_id) . '</h2>';
            if (!empty($dataset['description'])) {
                $output .= '<p>' . wp_kses_post($dataset['description']) . '</p>';
            }
            if (!empty($dataset['data'])) {
                $output .= '<table class="widefat"><tbody>';
                foreach ((array) $dataset['data'] as $row) {
                    $output .= '<tr>';
                    foreach ((array) $row as $value) {
                        $output .= '<td>' . esc_html((string) $value) . '</td>';
                    }
                    $output .= '</tr>';
                }
                $output .= '</tbody></table>';
            }
            if (is_array($visualizations) && !empty($visualizations)) {
                $output .= '<h3>' . esc_html__('Wizualizacje', 'open-data-plugin') . '</h3><ul>';
                foreach ($visualizations as $viz) {
                    $label = esc_html($viz['title'] ?? __('Wizualizacja', 'open-data-plugin'));
                    if (!empty($viz['url'])) {
                        $output .= '<li><a href="' . esc_url($viz['url']) . '" target="_blank" rel="noopener">' . $label . '</a></li>';
                    } else {
                        $output .= '<li>' . $label . '</li>';
                    }
                }
                $output .= '</ul>';
            } else {
                $output .= '<p><strong>' . esc_html__('BRAK MOŻLIWEJ WIZUALIZACJI', 'open-data-plugin') . '</strong></p>';
            }
            $output .= '</div>';
            return $output;
        }

        /**
         * Pomocnicza metoda pobierająca dane z API.
         * Technical description:
         *     Wykorzystuje `wp_remote_get`, ustawia nagłówki (Accept JSON:API,
         *     Authorization), obsługuje błędy i cache'uje odpowiedź na 5 minut.
         * Instructions for laika:
         *     "Wysyłamy zapytanie do serwera danych i zwracamy wynik jako tablicę." 
         * Example:
         *     `$this->fetch_from_api('/datasets');`
         * Effect for end user:
         *     Zapewnia stabilne i bezpieczne połączenie z backendem pluginu Python.
         *
         * @param string $path
         * @return array<string,mixed>|array<int,mixed>|null
         */
        private function fetch_from_api(string $path) {
            $api_base = rtrim(get_option('odp_api_base', ''), '/');
            if (empty($api_base)) {
                return null;
            }
            $cache_key = 'odp_cache_' . md5($path);
            $cached = get_transient($cache_key);
            if ($cached !== false) {
                return $cached;
            }
            $headers = [
                'Accept' => 'application/vnd.opendata.v1+json',
            ];
            $token = get_option('odp_api_token', '');
            if (!empty($token)) {
                $headers['Authorization'] = 'Bearer ' . $token;
            }
            $response = wp_remote_get($api_base . $path, [
                'headers' => $headers,
                'timeout' => 15,
            ]);
            if (is_wp_error($response)) {
                return null;
            }
            $code = (int) wp_remote_retrieve_response_code($response);
            if ($code >= 400) {
                return null;
            }
            $body = wp_remote_retrieve_body($response);
            $data = json_decode($body, true);
            if (!is_array($data)) {
                return null;
            }
            set_transient($cache_key, $data, 5 * MINUTE_IN_SECONDS);
            return $data;
        }
    }
}

Open_Data_Plugin::instance();
