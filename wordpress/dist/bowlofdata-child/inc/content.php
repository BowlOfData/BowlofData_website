<?php
/**
 * Content model: post types, taxonomies, meta, and URL parity with bowlofdata.net.
 *
 * Maps scripts/schema.sql onto WordPress:
 *   weeks     -> bod_issue    (post_name "30_2026")
 *   items     -> bod_story    (post_parent = issue, meta kind = article|paper)
 *   releases  -> bod_release  (post_parent = issue)
 *   category  -> bod_beat     taxonomy on bod_story
 *   item_tags -> bod_tech     taxonomy on bod_story
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * The five editorial beats. Mirrors build.py CATEGORY_ORDER / CATEGORY_META
 * (label, h1, intro only — keyword classification stays in Python at load time,
 * exactly as netlify/functions/_shared/topics.mjs does it).
 */
function bod_beats() {
	return array(
		'ai'          => array(
			'label' => 'AI & ML',
			'h1'    => 'AI & Machine Learning',
			'intro' => 'Every week, Bowl of Data tracks the AI and machine-learning stories that matter — new model releases, research that holds up, and where large models actually land in real products. Here is every issue\'s AI coverage, newest first.',
		),
		'governance'  => array(
			'label' => 'Data & AI Governance',
			'h1'    => 'Data & AI Governance',
			'intro' => 'Every week, Bowl of Data tracks the rules now shaping how data and AI get built and shipped — privacy regulation, the EU AI Act, automated-decision and data-broker law, and algorithmic accountability. Here is every issue\'s governance coverage, newest first.',
		),
		'security'    => array(
			'label' => 'Cybersecurity',
			'h1'    => 'Cybersecurity',
			'intro' => 'Every week, Bowl of Data tracks the vulnerabilities, exploits, and threat intelligence worth acting on — what to patch before it becomes someone else\'s headline. Here is every issue\'s security coverage, newest first.',
		),
		'blockchain'  => array(
			'label' => 'Blockchain & Crypto',
			'h1'    => 'Blockchain & Crypto',
			'intro' => 'Every week, Bowl of Data tracks the meaningful moves in blockchain and crypto — protocol upgrades, market shifts, and the regulation worth watching. Here is every issue\'s blockchain coverage, newest first.',
		),
		'engineering' => array(
			'label' => 'Software Engineering',
			'h1'    => 'Software Engineering',
			'intro' => 'Every week, Bowl of Data tracks the tools, frameworks, and open-source releases that change how we build software. Here is every issue\'s engineering coverage, newest first.',
		),
	);
}

/** The static pages, slug => [title, nav label]. Rewrites give them .html URLs. */
function bod_static_pages() {
	return array(
		'archive'  => 'Archive',
		'topics'   => 'Topics',
		'about'    => 'About',
		'team'     => 'Team',
		'contact'  => 'Contact',
		'services' => 'Services',
	);
}

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

add_action( 'init', 'bod_register_content', 5 );

/**
 * Register post types and taxonomies.
 *
 * All rewrites are declared false and replaced with explicit rules further
 * down, because WordPress cannot express a trailing ".html" on its own.
 */
function bod_register_content() {

	register_post_type(
		'bod_issue',
		array(
			'labels'             => array(
				'name'          => __( 'Issues', 'bowlofdata' ),
				'singular_name' => __( 'Issue', 'bowlofdata' ),
			),
			'public'             => true,
			'publicly_queryable' => true,
			'show_ui'            => true,
			'show_in_menu'       => true,
			'show_in_rest'       => true,
			'rest_base'          => 'bod_issue',
			'has_archive'        => false,
			'hierarchical'       => false,
			'query_var'          => 'bod_issue',
			'rewrite'            => false,
			'menu_icon'          => 'dashicons-book',
			'supports'           => array( 'title', 'custom-fields' ),
		)
	);

	register_post_type(
		'bod_story',
		array(
			'labels'             => array(
				'name'          => __( 'Stories', 'bowlofdata' ),
				'singular_name' => __( 'Story', 'bowlofdata' ),
			),
			// Stories render as cards inside their issue and have no page of
			// their own, matching bowlofdata.net where they are #anchors.
			'public'             => false,
			'publicly_queryable' => false,
			'show_ui'            => true,
			'show_in_menu'       => true,
			'show_in_rest'       => true,
			'rest_base'          => 'bod_story',
			'has_archive'        => false,
			// Hierarchical so a story can hang off its issue via post_parent.
			// This is load-bearing for REST: the parent field (and the parent
			// query filter) are only registered for hierarchical types, and a
			// non-hierarchical type drops "parent" from a create payload in
			// silence, orphaning every story.
			'hierarchical'       => true,
			'rewrite'            => false,
			'menu_icon'          => 'dashicons-media-text',
			'supports'           => array( 'title', 'editor', 'custom-fields', 'page-attributes' ),
			'taxonomies'         => array( 'bod_beat', 'bod_tech' ),
		)
	);

	register_post_type(
		'bod_release',
		array(
			'labels'             => array(
				'name'          => __( 'Model Releases', 'bowlofdata' ),
				'singular_name' => __( 'Model Release', 'bowlofdata' ),
			),
			'public'             => false,
			'publicly_queryable' => false,
			'show_ui'            => true,
			'show_in_menu'       => true,
			'show_in_rest'       => true,
			'rest_base'          => 'bod_release',
			'has_archive'        => false,
			'hierarchical'       => true, // See bod_story: needed for post_parent over REST.
			'rewrite'            => false,
			'menu_icon'          => 'dashicons-superhero',
			'supports'           => array( 'title', 'custom-fields', 'page-attributes' ),
		)
	);

	register_taxonomy(
		'bod_beat',
		array( 'bod_story' ),
		array(
			'labels'            => array(
				'name'          => __( 'Beats', 'bowlofdata' ),
				'singular_name' => __( 'Beat', 'bowlofdata' ),
			),
			'public'            => true,
			'hierarchical'      => false,
			'show_in_rest'      => true,
			'rest_base'         => 'bod_beat',
			'show_admin_column' => true,
			'query_var'         => 'bod_beat',
			'rewrite'           => false,
		)
	);

	register_taxonomy(
		'bod_tech',
		array( 'bod_story' ),
		array(
			'labels'            => array(
				'name'          => __( 'Technologies', 'bowlofdata' ),
				'singular_name' => __( 'Technology', 'bowlofdata' ),
			),
			'public'            => true,
			'hierarchical'      => false,
			'show_in_rest'      => true,
			'rest_base'         => 'bod_tech',
			'show_admin_column' => true,
			'query_var'         => 'bod_tech',
			'rewrite'           => false,
		)
	);

	bod_register_meta();
	bod_register_rewrites();
}

/**
 * Expose every field the publisher writes to the REST API.
 *
 * Array-valued columns from Postgres (long_resume_paragraphs, technologies,
 * key_features) are stored as JSON strings — a single scalar meta round-trips
 * through REST cleanly, where a repeated meta would not.
 */
function bod_register_meta() {
	$string = array(
		'type'         => 'string',
		'single'       => true,
		'default'      => '',
		'show_in_rest' => true,
		'auth_callback' => static function () {
			return current_user_can( 'edit_posts' );
		},
	);
	$number = array_merge( $string, array( 'type' => 'number', 'default' => 0 ) );

	// bod_issue. preview_titles is the JSON list of 3 headlines the archive
	// cards show; article_count is denormalised so the archive needs one query
	// rather than one per issue (both mirror build.py _read_all_weeks).
	foreach ( array( 'label', 'month_name', 'preview_titles' ) as $key ) {
		register_post_meta( 'bod_issue', 'bod_' . $key, $string );
	}
	foreach ( array( 'week', 'year', 'month', 'source_mtime', 'sort_key', 'article_count' ) as $key ) {
		register_post_meta( 'bod_issue', 'bod_' . $key, $number );
	}

	// bod_story
	foreach ( array( 'kind', 'url', 'source', 'published', 'short_summary', 'main_topic', 'long_resume_paragraphs', 'technologies', 'category', 'category_label' ) as $key ) {
		register_post_meta( 'bod_story', 'bod_' . $key, $string );
	}
	foreach ( array( 'position', 'quality_score', 'week', 'year', 'sort_key' ) as $key ) {
		register_post_meta( 'bod_story', 'bod_' . $key, $number );
	}

	// bod_release
	foreach ( array( 'provider', 'model_name', 'release_date', 'summary', 'url', 'key_features' ) as $key ) {
		register_post_meta( 'bod_release', 'bod_' . $key, $string );
	}
	foreach ( array( 'position', 'week', 'year' ) as $key ) {
		register_post_meta( 'bod_release', 'bod_' . $key, $number );
	}
}

// ---------------------------------------------------------------------------
// URL parity: /week/30_2026.html, /topic/ai.html, /tag/python.html, /about.html
// ---------------------------------------------------------------------------

/**
 * Register the .html rewrite rules.
 *
 * Verified on Altervista: a nonexistent .html path reaches WordPress rather
 * than dying in Apache, so these rules do get a chance to match.
 */
function bod_register_rewrites() {
	add_rewrite_rule( '^week/([^/]+)\.html$', 'index.php?post_type=bod_issue&name=$matches[1]', 'top' );
	add_rewrite_rule( '^topic/([^/]+)\.html$', 'index.php?bod_beat=$matches[1]', 'top' );
	add_rewrite_rule( '^tag/([^/]+)\.html$', 'index.php?bod_tech=$matches[1]', 'top' );
	add_rewrite_rule( '^index\.html$', 'index.php', 'top' );

	foreach ( array_keys( bod_static_pages() ) as $slug ) {
		add_rewrite_rule( '^' . $slug . '\.html$', 'index.php?pagename=' . $slug, 'top' );
	}
}

/** Flush rules once on activation so the new URLs resolve immediately. */
add_action(
	'after_switch_theme',
	static function () {
		bod_register_content();
		bod_seed_beat_terms();
		flush_rewrite_rules();
	}
);

/** Issue permalinks: /week/30_2026.html */
add_filter(
	'post_type_link',
	static function ( $link, $post ) {
		if ( $post instanceof WP_Post && 'bod_issue' === $post->post_type && $post->post_name ) {
			return home_url( '/week/' . $post->post_name . '.html' );
		}
		return $link;
	},
	10,
	2
);

/** Term permalinks: /topic/ai.html and /tag/python.html */
add_filter(
	'term_link',
	static function ( $link, $term, $taxonomy ) {
		if ( 'bod_beat' === $taxonomy ) {
			return home_url( '/topic/' . $term->slug . '.html' );
		}
		if ( 'bod_tech' === $taxonomy ) {
			return home_url( '/tag/' . $term->slug . '.html' );
		}
		return $link;
	},
	10,
	3
);

/** Static page permalinks: /archive.html rather than /archive/ */
add_filter(
	'page_link',
	static function ( $link, $post_id ) {
		$post = get_post( $post_id );
		if ( $post && array_key_exists( $post->post_name, bod_static_pages() ) && ! $post->post_parent ) {
			return home_url( '/' . $post->post_name . '.html' );
		}
		return $link;
	},
	10,
	2
);

/**
 * Stop WordPress "correcting" /archive.html to /archive/. Without this the
 * canonical redirect undoes the rules above on every request.
 */
add_filter(
	'redirect_canonical',
	static function ( $redirect_url, $requested_url ) {
		if ( is_string( $requested_url ) && preg_match( '#\.html(\?|$)#', $requested_url ) ) {
			return false;
		}
		return $redirect_url;
	},
	10,
	2
);

/**
 * Technology pages exist only past the same threshold the rest of the system
 * uses (build.py _collect_tags min_items=3, db.mjs keptTagSlugs, tag.mjs 404).
 * This is the single place that rule lives in the WordPress port.
 *
 * @param WP_Term|int $term Term or term ID.
 */
function bod_tech_is_public( $term ) {
	$term = is_numeric( $term ) ? get_term( (int) $term, 'bod_tech' ) : $term;
	if ( ! $term || is_wp_error( $term ) ) {
		return false;
	}
	return (int) $term->count >= BOD_MIN_TAG_ITEMS;
}

/** Serve a real 404 for thin technology terms. */
add_action(
	'template_redirect',
	static function () {
		if ( ! is_tax( 'bod_tech' ) ) {
			return;
		}
		$term = get_queried_object();
		if ( $term instanceof WP_Term && ! bod_tech_is_public( $term ) ) {
			global $wp_query;
			$wp_query->set_404();
			status_header( 404 );
			nocache_headers();
			include get_query_template( '404' );
			exit;
		}
	}
);

// ---------------------------------------------------------------------------
// Seeding
// ---------------------------------------------------------------------------

/** Create the five beat terms with their label/h1/intro as term meta. */
function bod_seed_beat_terms() {
	foreach ( bod_beats() as $slug => $meta ) {
		$term = get_term_by( 'slug', $slug, 'bod_beat' );
		if ( ! $term ) {
			$created = wp_insert_term( $meta['label'], 'bod_beat', array( 'slug' => $slug ) );
			if ( is_wp_error( $created ) ) {
				continue;
			}
			$term_id = $created['term_id'];
		} else {
			$term_id = $term->term_id;
		}
		update_term_meta( $term_id, 'bod_label', $meta['label'] );
		update_term_meta( $term_id, 'bod_h1', $meta['h1'] );
		update_term_meta( $term_id, 'bod_intro', $meta['intro'] );
	}
}
