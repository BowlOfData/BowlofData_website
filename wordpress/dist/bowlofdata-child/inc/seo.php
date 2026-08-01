<?php
/**
 * SEO for a mirror install.
 *
 * bowlofdata.net stays canonical, so every page here points back at its .net
 * twin. The theme emits its own title, meta, Open Graph and JSON-LD (ports of
 * build.py's builders), which means Yoast must not emit a competing set —
 * otherwise pages ship two titles, two canonicals and two schema graphs.
 *
 * The XML sitemap is ours too. Yoast built its sitemap from every registered
 * term, but a bod_tech term only earns a page past BOD_MIN_TAG_ITEMS — so it
 * advertised ~1,270 URLs that answer 404, and stamped every lastmod with the
 * backfill script's write time. bod_sitemap_xml() below is generated from the
 * same helpers the templates render from, which makes listing a URL that does
 * not exist impossible rather than merely fixed.
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

// ---------------------------------------------------------------------------
// Yoast: emit nothing
// ---------------------------------------------------------------------------

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
 * Turn Yoast's sitemaps off, then empty them out anyway.
 *
 * wpseo_enable_xml_sitemap is the blunt switch but is absent from Yoast's
 * documented API, so it is not load-bearing on its own. The two exclusion
 * filters below are documented and cover every post type and taxonomy this
 * install registers, so Yoast produces nothing even if the switch is ignored.
 */
add_filter( 'wpseo_enable_xml_sitemap', '__return_false' );

add_filter(
	'wpseo_sitemap_exclude_post_type',
	static function ( $excluded, $post_type ) {
		return in_array( $post_type, array( 'page', 'post', 'bod_issue', 'bod_story', 'bod_release', 'attachment' ), true )
			? true
			: $excluded;
	},
	10,
	2
);

add_filter(
	'wpseo_sitemap_exclude_taxonomy',
	static function ( $excluded, $taxonomy ) {
		return in_array( $taxonomy, array( 'bod_beat', 'bod_tech', 'category', 'post_tag' ), true )
			? true
			: $excluded;
	},
	10,
	2
);

// ---------------------------------------------------------------------------
// Canonical helpers
// ---------------------------------------------------------------------------

/**
 * Map the current request to its bowlofdata.net path.
 *
 * Used by templates that have not set an explicit canonical.
 */
function bod_canonical_for_request() {
	$path = wp_parse_url( home_url( add_query_arg( array() ) ), PHP_URL_PATH );
	return bod_canonical( $path ? $path : '/' );
}

/** Slugs of the pages that exist on bowlofdata.net, front page included. */
function bod_is_mirrored_page( $post = null ) {
	$post = get_post( $post );
	if ( ! $post || 'page' !== $post->post_type ) {
		return false;
	}
	if ( (int) get_option( 'page_on_front' ) === (int) $post->ID ) {
		return true;
	}
	return array_key_exists( $post->post_name, bod_static_pages() ) && ! $post->post_parent;
}

// ---------------------------------------------------------------------------
// XML sitemap — the PHP twin of build.py _generate_sitemap()
// ---------------------------------------------------------------------------

/** Query var that routes /sitemap.xml to bod_render_sitemap(). */
add_filter(
	'query_vars',
	static function ( $vars ) {
		$vars[] = 'bod_sitemap';
		return $vars;
	}
);

/**
 * Newest source_mtime per beat and technology term.
 *
 * One pass over every story rather than a query per term: with ~1,400 terms the
 * per-term route would run 1,400 queries to build one sitemap. Returns
 * array( 'bod_beat' => array( slug => mtime ), 'bod_tech' => array( … ) ).
 */
function bod_term_mtimes() {
	$issue_mtime = array();
	foreach ( bod_all_issues() as $issue ) {
		$issue_mtime[ (int) $issue['id'] ] = (float) $issue['source_mtime'];
	}

	$stories = get_posts(
		array(
			'post_type'        => 'bod_story',
			'post_status'      => 'publish',
			'posts_per_page'   => -1,
			'suppress_filters' => false,
		)
	);
	if ( ! $stories ) {
		return array(
			'bod_beat' => array(),
			'bod_tech' => array(),
		);
	}

	$story_mtime = array();
	foreach ( $stories as $story ) {
		$parent = (int) $story->post_parent;
		if ( isset( $issue_mtime[ $parent ] ) ) {
			$story_mtime[ $story->ID ] = $issue_mtime[ $parent ];
		}
	}

	$out = array(
		'bod_beat' => array(),
		'bod_tech' => array(),
	);
	if ( ! $story_mtime ) {
		return $out;
	}

	$rels = wp_get_object_terms(
		array_keys( $story_mtime ),
		array( 'bod_beat', 'bod_tech' ),
		array( 'fields' => 'all_with_object_id' )
	);
	if ( is_wp_error( $rels ) || ! is_array( $rels ) ) {
		return $out;
	}

	foreach ( $rels as $term ) {
		$mtime = $story_mtime[ $term->object_id ] ?? 0;
		$known = $out[ $term->taxonomy ][ $term->slug ] ?? 0;
		if ( $mtime > $known ) {
			$out[ $term->taxonomy ][ $term->slug ] = $mtime;
		}
	}

	return $out;
}

/**
 * Every URL this install publishes, as array( loc, changefreq, priority, lastmod ).
 *
 * Sourced from the same helpers the templates render from — bod_static_pages(),
 * bod_public_beat_terms(), bod_public_tech_terms(), bod_all_issues() — so a URL
 * can only be listed when its page exists. Mirrors build.py _generate_sitemap().
 */
function bod_sitemap_entries() {
	$day = static function ( $mtime ) {
		return $mtime ? gmdate( 'Y-m-d', (int) $mtime ) : null;
	};

	$issues = bod_all_issues();
	$newest = $issues ? (float) $issues[0]['source_mtime'] : 0;
	$mtimes = bod_term_mtimes();

	// Static pages. The landing page and the two indexes turn over with each
	// issue; the marketing pages genuinely do not, so they carry no lastmod
	// rather than a build timestamp that would claim they changed.
	$entries = array(
		array( bod_url( '/' ), 'weekly', '1.0', $day( $newest ) ),
		array( bod_url( '/archive.html' ), 'weekly', '0.9', $day( $newest ) ),
		array( bod_url( '/topics.html' ), 'weekly', '0.8', $day( $newest ) ),
		array( bod_url( '/services.html' ), 'monthly', '0.7', null ),
		array( bod_url( '/about.html' ), 'monthly', '0.6', null ),
		array( bod_url( '/team.html' ), 'monthly', '0.5', null ),
		array( bod_url( '/contact.html' ), 'monthly', '0.5', null ),
	);

	foreach ( bod_public_beat_terms() as $term ) {
		$entries[] = array(
			bod_url( '/topic/' . $term->slug . '.html' ),
			'weekly',
			'0.8',
			$day( $mtimes['bod_beat'][ $term->slug ] ?? 0 ),
		);
	}

	foreach ( bod_public_tech_terms() as $term ) {
		$entries[] = array(
			bod_url( '/tag/' . $term->slug . '.html' ),
			'weekly',
			'0.6',
			$day( $mtimes['bod_tech'][ $term->slug ] ?? 0 ),
		);
	}

	foreach ( $issues as $issue ) {
		$entries[] = array(
			bod_url( '/' . $issue['href'] ),
			'never',
			'0.8',
			$day( $issue['source_mtime'] ),
		);
	}

	return $entries;
}

/** Render the sitemap. Cached — it only changes when an issue is published. */
function bod_sitemap_xml() {
	$cached = get_transient( 'bod_sitemap_xml' );
	if ( is_string( $cached ) && '' !== $cached ) {
		return $cached;
	}

	$lines = array(
		'<?xml version="1.0" encoding="UTF-8"?>',
		'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
	);
	foreach ( bod_sitemap_entries() as $entry ) {
		list( $loc, $changefreq, $priority, $lastmod ) = $entry;
		$lines[] = '  <url>';
		$lines[] = '    <loc>' . esc_url( $loc ) . '</loc>';
		$lines[] = '    <changefreq>' . $changefreq . '</changefreq>';
		$lines[] = '    <priority>' . $priority . '</priority>';
		if ( $lastmod ) {
			$lines[] = '    <lastmod>' . $lastmod . '</lastmod>';
		}
		$lines[] = '  </url>';
	}
	$lines[] = '</urlset>';

	$xml = implode( "\n", $lines ) . "\n";
	set_transient( 'bod_sitemap_xml', $xml, DAY_IN_SECONDS );

	return $xml;
}

/** Publishing anything the sitemap covers invalidates it. */
foreach ( array( 'save_post_bod_issue', 'save_post_bod_story', 'deleted_post', 'edited_bod_tech', 'edited_bod_beat' ) as $bod_hook ) {
	add_action(
		$bod_hook,
		static function () {
			delete_transient( 'bod_sitemap_xml' );
		}
	);
}
unset( $bod_hook );

/**
 * Serve /sitemap.xml.
 *
 * Priority 0 so it answers before the redirects below get a look at the request.
 */
add_action(
	'template_redirect',
	static function () {
		if ( ! get_query_var( 'bod_sitemap' ) ) {
			return;
		}
		header( 'Content-Type: application/xml; charset=UTF-8' );
		header( 'X-Robots-Tag: noindex, follow', true );
		echo bod_sitemap_xml(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- XML, escaped per node.
		exit;
	},
	0
);

/**
 * Point robots.txt at our sitemap, and only ours.
 *
 * PHP_INT_MAX because Yoast appends its own block — including a Sitemap line
 * for the sitemap index we just turned off — on a later priority than 99.
 * Running last is the only way to strip it.
 */
add_filter(
	'robots_txt',
	static function ( $output ) {
		$kept = array();
		foreach ( preg_split( '/\r\n|\r|\n/', (string) $output ) as $line ) {
			if ( ! preg_match( '/^\s*sitemap\s*:/i', $line ) ) {
				$kept[] = $line;
			}
		}
		$output = rtrim( implode( "\n", $kept ) );

		return $output . "\n\nSitemap: " . bod_url( '/sitemap.xml' ) . "\n";
	},
	PHP_INT_MAX
);

// ---------------------------------------------------------------------------
// Robots directives
// ---------------------------------------------------------------------------

/**
 * noindex anything outside the mirror's canonical URL set.
 *
 * follow stays on: these pages still link into real ones, and we want that
 * link equity to flow rather than dead-end. The sitemap already omits them;
 * this covers whatever a crawler reaches by other means.
 */
add_filter(
	'wp_robots',
	static function ( $robots ) {
		$off_map = is_search() || is_author() || is_date() || is_paged() || is_feed();
		if ( ! $off_map && is_page() && ! bod_is_mirrored_page() ) {
			$off_map = true;
		}
		if ( $off_map ) {
			$robots['noindex'] = true;
			$robots['follow']  = true;
		}
		return $robots;
	}
);

// ---------------------------------------------------------------------------
// Redirects: one URL per page
// ---------------------------------------------------------------------------

/**
 * 301 /about/ to /about.html.
 *
 * inc/content.php filters page_link so every link we emit already uses .html,
 * and suppresses redirect_canonical for URLs that end in .html — but the
 * pretty permalink still resolves, so each of the six static pages answers 200
 * at two URLs. This closes the second one.
 */
add_action(
	'template_redirect',
	static function () {
		if ( ! is_page() || is_front_page() || is_404() ) {
			return;
		}

		$post = get_post();
		if ( ! $post || ! array_key_exists( $post->post_name, bod_static_pages() ) || $post->post_parent ) {
			return;
		}

		$path = (string) wp_parse_url( isset( $_SERVER['REQUEST_URI'] ) ? esc_url_raw( wp_unslash( $_SERVER['REQUEST_URI'] ) ) : '/', PHP_URL_PATH );
		if ( preg_match( '#\.html$#', $path ) ) {
			return;
		}

		wp_safe_redirect( bod_url( '/' . $post->post_name . '.html' ), 301 );
		exit;
	},
	5
);

/**
 * Send WordPress's own feeds to the canonical one — but only while mirroring.
 *
 * When this install is canonical there is no feed elsewhere to defer to, and
 * redirecting would point subscribers at a URL that does not exist. The comment
 * feed goes either way: nothing here accepts comments.
 */
add_action(
	'template_redirect',
	static function () {
		if ( ! is_feed() ) {
			return;
		}
		if ( BOD_IS_MIRROR ) {
			wp_redirect( bod_feed_url(), 301 ); // phpcs:ignore WordPress.Security.SafeRedirect.wp_redirect_wp_redirect -- deliberate cross-domain redirect to the canonical origin.
			exit;
		}
		if ( is_comment_feed() ) {
			wp_safe_redirect( bod_feed_url(), 301 );
			exit;
		}
	},
	5
);

/**
 * Stop advertising WordPress's feed discovery links.
 *
 * header.php emits a single <link rel=alternate> pointing at bod_feed_url();
 * core's feed_links() adds a competing pair, including a comment feed.
 */
add_action(
	'init',
	static function () {
		remove_action( 'wp_head', 'feed_links', 2 );
		remove_action( 'wp_head', 'feed_links_extra', 3 );
	}
);
