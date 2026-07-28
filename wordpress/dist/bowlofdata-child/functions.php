<?php
/**
 * Bowl of Data — Blocksy child theme.
 *
 * Ports the bowlofdata.net layout to WordPress. The templates render the whole
 * document themselves (DOCTYPE to </html>) rather than reusing Blocksy's shell,
 * so Blocksy is present only as a valid parent; its markup and CSS are dropped.
 *
 * Source of truth for the markup is netlify/functions/_shared/render.mjs in the
 * website repo. Keep inc/render.php in step with it.
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'BOD_VERSION', '1.0.0' );
define( 'BOD_SITE_NAME', 'Bowl of Data' );
define( 'BOD_SITE_TAGLINE', 'A weekly digest of the most relevant tech stories' );
define( 'BOD_PODCAST_URL', 'https://open.spotify.com/show/033Mqus9YAIssepHakRIIk' );
define( 'BOD_SUBSTACK_URL', 'https://bowlofdata.substack.com/' );

/**
 * This install is a mirror: bowlofdata.net stays canonical. Every page emits a
 * canonical (and og:url) pointing at the matching .net URL.
 */
define( 'BOD_CANONICAL_ORIGIN', 'https://bowlofdata.net' );

/** A technology term needs this many stories before it gets a public page. */
define( 'BOD_MIN_TAG_ITEMS', 3 );

require_once get_stylesheet_directory() . '/inc/content.php';
require_once get_stylesheet_directory() . '/inc/query.php';
require_once get_stylesheet_directory() . '/inc/render.php';
require_once get_stylesheet_directory() . '/inc/seo.php';
require_once get_stylesheet_directory() . '/inc/contact.php';

/**
 * Theme supports. Deliberately minimal — the templates emit their own markup.
 */
add_action(
	'after_setup_theme',
	static function () {
		// No 'title-tag' support on purpose: header.php prints <title> itself so
		// the text matches bowlofdata.net exactly, and wp_head() must not add a
		// second one.
		add_theme_support( 'post-thumbnails' );
		add_theme_support( 'html5', array( 'style', 'script' ) );
		register_nav_menus( array( 'bod_primary' => __( 'Primary', 'bowlofdata' ) ) );
	}
);

/**
 * Drop the parent theme's CSS and WordPress's block/emoji payload, then load
 * the design system. Runs late so it wins against Blocksy and its companion.
 */
add_action(
	'wp_enqueue_scripts',
	static function () {
		$parent_uri = get_template_directory_uri();

		foreach ( wp_styles()->queue as $handle ) {
			$style = wp_styles()->registered[ $handle ] ?? null;
			if ( $style && ! empty( $style->src ) && false !== strpos( $style->src, $parent_uri ) ) {
				wp_dequeue_style( $handle );
			}
		}

		foreach ( array( 'wp-block-library', 'wp-block-library-theme', 'global-styles', 'classic-theme-styles' ) as $handle ) {
			wp_dequeue_style( $handle );
		}

		wp_enqueue_style(
			'bod-fonts',
			'https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;700;800&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&family=JetBrains+Mono:wght@500;600&display=swap',
			array(),
			null // phpcs:ignore WordPress.WP.EnqueuedResourceParameters.MissingVersion -- Google Fonts URLs are versioned by their query string.
		);

		wp_enqueue_style( 'bod-style', get_stylesheet_uri(), array( 'bod-fonts' ), BOD_VERSION );
	},
	100
);

/** Emoji detection scripts add nothing here and cost a request. */
add_action(
	'init',
	static function () {
		remove_action( 'wp_head', 'print_emoji_detection_script', 7 );
		remove_action( 'wp_print_styles', 'print_emoji_styles' );
		remove_action( 'wp_head', 'wp_generator' );
		remove_action( 'wp_head', 'wlwmanifest_link' );
		remove_action( 'wp_head', 'rsd_link' );
	}
);

/**
 * Blocksy Companion injects its own markup on some hooks. Our templates never
 * call the parent's header/footer, but its content-block hooks can still fire.
 */
add_action(
	'wp_loaded',
	static function () {
		remove_all_actions( 'blocksy:content-block:render' );
	}
);
