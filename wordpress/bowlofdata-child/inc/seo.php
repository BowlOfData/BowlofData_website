<?php
/**
 * SEO for a mirror install.
 *
 * bowlofdata.net stays canonical, so every page here points back at its .net
 * twin. The theme emits its own title, meta, Open Graph and JSON-LD (ports of
 * build.py's builders), which means Yoast must not emit a competing set —
 * otherwise pages ship two titles, two canonicals and two schema graphs.
 *
 * Yoast's XML sitemaps are left alone: listing the Altervista URLs is correct
 * for a canonicalised mirror.
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Drop every Yoast <head> presenter. We own the head.
 *
 * This covers title, canonical, robots, Open Graph, Twitter and schema in one
 * filter, rather than chasing each tag individually.
 */
add_filter( 'wpseo_frontend_presenters', '__return_empty_array' );

/** Belt and braces, in case a presenter is reinstated by an update. */
add_filter( 'wpseo_json_ld_output', '__return_false' );

/**
 * If anything downstream still asks Yoast for a canonical, give it ours.
 */
add_filter(
	'wpseo_canonical',
	static function () {
		$context = bod_page_context();
		return $context['canonical'];
	}
);

/**
 * Map the current request to its bowlofdata.net path.
 *
 * Used by templates that have not set an explicit canonical.
 */
function bod_canonical_for_request() {
	$path = wp_parse_url( home_url( add_query_arg( array() ) ), PHP_URL_PATH );
	return bod_canonical( $path ? $path : '/' );
}
