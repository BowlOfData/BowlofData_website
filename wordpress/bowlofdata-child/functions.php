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
define( 'BOD_YOUTUBE_URL', 'https://www.youtube.com/@bowlofdata' );

/**
 * The origin every canonical points at.
 *
 * Resolved 2026-08-12. Between 2026-08-01 and now, bowlofdata.net was pointed
 * at Netlify and serves real deep paths again (/week/32_2026.html returns 200),
 * so the interim self-canonical put in place while .net was an Aruba
 * domain-forward is no longer needed — and this install no longer has a job.
 * See BOD_RETIRED_TO below.
 */
define( 'BOD_CANONICAL_ORIGIN', 'https://bowlofdata.net' );

/** True when canonicals point at some other install (the mirror arrangement). */
define( 'BOD_IS_MIRROR', BOD_CANONICAL_ORIGIN !== untrailingslashit( home_url() ) );

/**
 * Where this install has been retired to, or '' to keep serving pages.
 *
 * This WordPress port existed only because bowlofdata.net could not serve deep
 * paths. It can now, so two sites were publishing identical titles and identical
 * sitemaps at identical paths, splitting the authority for every query between
 * them. Everything here 301s to its .net twin; the canonical above is only a
 * fallback for the case where this is switched back off.
 */
define( 'BOD_RETIRED_TO', 'https://bowlofdata.net' );

/**
 * Send every front-end request to the canonical site.
 *
 * template_redirect only fires while loading a front-end template, so wp-admin,
 * wp-login and the REST API are untouched and scripts/deploy_wp_theme.py keeps
 * working. robots.txt is the one front-end response that must survive: WordPress
 * serves it through the template loader *after* this hook, and a crawler that
 * cannot fetch robots.txt never crawls the pages, never sees these 301s, and
 * never consolidates anything. Feeds and the sitemap redirect on purpose — that
 * carries subscribers and crawlers to the real equivalents.
 */
add_action(
	'template_redirect',
	static function () {
		if ( ! BOD_RETIRED_TO || is_robots() || is_favicon() ) {
			return;
		}
		$path = isset( $_SERVER['REQUEST_URI'] ) ? wp_unslash( $_SERVER['REQUEST_URI'] ) : '/';
		wp_redirect( untrailingslashit( BOD_RETIRED_TO ) . $path, 301 );
		exit;
	},
	0
);

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

		// Not dequeued here: blocksy-dynamic-global-css (12 KB from
		// wp-content/uploads/blocksy/). Blocksy Companion re-adds it after this
		// hook and after wp_print_styles, so neither dequeue nor deregister
		// sticks. Left loading deliberately rather than shipping a no-op.

		// Contact Form 7 ships on every page for the sake of one form.
		if ( ! is_page( 'contact' ) ) {
			wp_dequeue_style( 'contact-form-7' );
			wp_dequeue_script( 'contact-form-7' );
			wp_dequeue_script( 'swv' );
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

/**
 * Head cruft that costs requests and says nothing about the content: emoji
 * detection, the generator tag, and the oEmbed/REST/shortlink discovery links
 * for endpoints no mirrored page uses.
 */
add_action(
	'init',
	static function () {
		remove_action( 'wp_head', 'print_emoji_detection_script', 7 );
		remove_action( 'wp_print_styles', 'print_emoji_styles' );
		remove_action( 'wp_head', 'wp_generator' );
		remove_action( 'wp_head', 'wlwmanifest_link' );
		remove_action( 'wp_head', 'rsd_link' );
		remove_action( 'wp_head', 'wp_oembed_add_discovery_links' );
		remove_action( 'wp_head', 'rest_output_link_wp_head', 10 );
		remove_action( 'wp_head', 'wp_shortlink_wp_head', 10 );
	}
);

/**
 * Never render a Blocksy template.
 *
 * index.php alone is not enough: the hierarchy checks page.php and singular.php
 * first, and both exist in the parent, so untemplated content rendered Blocksy's
 * body markup inside our shell. Every real URL here resolves to a child
 * template (front-page, page-*, single-bod_issue, taxonomy-*, 404), so a
 * template that resolved out of the parent means content we do not mirror —
 * hand it to our fallback instead.
 */
add_filter(
	'template_include',
	static function ( $template ) {
		$parent = trailingslashit( get_template_directory() );
		if ( $template && 0 === strpos( $template, $parent ) ) {
			return get_stylesheet_directory() . '/index.php';
		}
		return $template;
	},
	99
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
