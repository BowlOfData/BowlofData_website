<?php
/**
 * Data access: turns WordPress posts into the plain arrays the renderers use.
 *
 * The array shapes deliberately match the row shapes the Netlify functions get
 * back from Postgres, so inc/render.php can stay a close transliteration of
 * netlify/functions/_shared/render.mjs.
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/** Decode a JSON-encoded meta value into a list, tolerating empty/garbage. */
function bod_meta_list( $post_id, $key ) {
	$raw = get_post_meta( $post_id, $key, true );
	if ( ! $raw ) {
		return array();
	}
	if ( is_array( $raw ) ) {
		return $raw;
	}
	$decoded = json_decode( (string) $raw, true );
	return is_array( $decoded ) ? $decoded : array();
}

/** "Week 30 · 2026" — mirrors build.py _week_label. */
function bod_week_label( $week, $year ) {
	return sprintf( 'Week %02d · %d', (int) $week, (int) $year );
}

/** "week/30_2026.html" — mirrors build.py _week_href. */
function bod_week_href( $week, $year ) {
	return sprintf( 'week/%02d_%d.html', (int) $week, (int) $year );
}

/**
 * Issue post -> array( week, year, label, href, source_mtime, article_count, ... ).
 *
 * @param WP_Post|int $issue Issue post.
 */
function bod_issue_data( $issue ) {
	$issue = get_post( $issue );
	if ( ! $issue || 'bod_issue' !== $issue->post_type ) {
		return null;
	}

	$week = (int) get_post_meta( $issue->ID, 'bod_week', true );
	$year = (int) get_post_meta( $issue->ID, 'bod_year', true );

	$count = get_post_meta( $issue->ID, 'bod_article_count', true );
	if ( '' === $count ) {
		$count = count( bod_issue_stories( $issue->ID, 'article' ) );
	}

	return array(
		'id'             => $issue->ID,
		'week'           => $week,
		'year'           => $year,
		'month'          => (int) get_post_meta( $issue->ID, 'bod_month', true ),
		'month_name'     => (string) get_post_meta( $issue->ID, 'bod_month_name', true ),
		'label'          => get_post_meta( $issue->ID, 'bod_label', true ) ?: bod_week_label( $week, $year ),
		'href'           => bod_week_href( $week, $year ),
		'permalink'      => get_permalink( $issue ),
		'source_mtime'   => (float) get_post_meta( $issue->ID, 'bod_source_mtime', true ),
		'article_count'  => (int) $count,
		'preview_titles' => bod_meta_list( $issue->ID, 'bod_preview_titles' ),
	);
}

/**
 * Stories belonging to an issue, in publication order.
 *
 * @param int    $issue_id Parent issue.
 * @param string $kind     'article' or 'paper'.
 */
function bod_issue_stories( $issue_id, $kind = 'article' ) {
	$posts = get_posts(
		array(
			'post_type'      => 'bod_story',
			'post_parent'    => (int) $issue_id,
			'posts_per_page' => -1,
			'orderby'        => array( 'menu_order' => 'ASC', 'ID' => 'ASC' ),
			'post_status'    => 'publish',
			'meta_query'     => array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query
				array(
					'key'   => 'bod_kind',
					'value' => $kind,
				),
			),
		)
	);

	return array_map( 'bod_story_data', $posts );
}

/**
 * Story post -> the array shape bod_article_card() expects.
 *
 * @param WP_Post $post Story post.
 */
function bod_story_data( $post ) {
	$post = get_post( $post );
	if ( ! $post ) {
		return null;
	}

	$techs = bod_meta_list( $post->ID, 'bod_technologies' );
	if ( ! $techs ) {
		// Fall back to the taxonomy if the denormalised copy is missing.
		$terms = get_the_terms( $post->ID, 'bod_tech' );
		$techs = is_array( $terms ) ? wp_list_pluck( $terms, 'name' ) : array();
	}

	return array(
		'id'                     => $post->ID,
		'slug'                   => $post->post_name,
		'title'                  => $post->post_title,
		'kind'                   => (string) get_post_meta( $post->ID, 'bod_kind', true ),
		'url'                    => (string) get_post_meta( $post->ID, 'bod_url', true ),
		'source'                 => (string) get_post_meta( $post->ID, 'bod_source', true ),
		'published'              => (string) get_post_meta( $post->ID, 'bod_published', true ),
		'short_summary'          => (string) get_post_meta( $post->ID, 'bod_short_summary', true ),
		'main_topic'             => (string) get_post_meta( $post->ID, 'bod_main_topic', true ),
		'long_resume_paragraphs' => bod_meta_list( $post->ID, 'bod_long_resume_paragraphs' ),
		'technologies'           => $techs,
		'category'               => (string) get_post_meta( $post->ID, 'bod_category', true ),
		'category_label'         => (string) get_post_meta( $post->ID, 'bod_category_label', true ),
		'quality_score'          => get_post_meta( $post->ID, 'bod_quality_score', true ),
	);
}

/**
 * Model releases belonging to an issue, in order.
 *
 * @param int $issue_id Parent issue.
 */
function bod_issue_releases( $issue_id ) {
	$posts = get_posts(
		array(
			'post_type'      => 'bod_release',
			'post_parent'    => (int) $issue_id,
			'posts_per_page' => -1,
			'orderby'        => array( 'menu_order' => 'ASC', 'ID' => 'ASC' ),
			'post_status'    => 'publish',
		)
	);

	return array_map(
		static function ( $post ) {
			return array(
				'slug'         => $post->post_name,
				'provider'     => (string) get_post_meta( $post->ID, 'bod_provider', true ),
				'model_name'   => get_post_meta( $post->ID, 'bod_model_name', true ) ?: $post->post_title,
				'release_date' => (string) get_post_meta( $post->ID, 'bod_release_date', true ),
				'summary'      => (string) get_post_meta( $post->ID, 'bod_summary', true ),
				'url'          => (string) get_post_meta( $post->ID, 'bod_url', true ),
				'key_features' => bod_meta_list( $post->ID, 'bod_key_features' ),
			);
		},
		$posts
	);
}

/**
 * Previous (older) or next (newer) issue, ordered by year+week.
 *
 * @param int    $sort_key  year * 100 + week of the current issue.
 * @param string $direction 'prev' or 'next'.
 */
function bod_adjacent_issue( $sort_key, $direction = 'prev' ) {
	$posts = get_posts(
		array(
			'post_type'      => 'bod_issue',
			'posts_per_page' => 1,
			'post_status'    => 'publish',
			'meta_key'       => 'bod_sort_key', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key
			'orderby'        => 'meta_value_num',
			'order'          => 'prev' === $direction ? 'DESC' : 'ASC',
			'meta_query'     => array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query
				array(
					'key'     => 'bod_sort_key',
					'value'   => (int) $sort_key,
					'type'    => 'NUMERIC',
					'compare' => 'prev' === $direction ? '<' : '>',
				),
			),
		)
	);

	if ( ! $posts ) {
		return null;
	}
	$data = bod_issue_data( $posts[0] );
	return array(
		'href'  => $data['href'],
		'label' => $data['label'],
	);
}

/**
 * Every issue, newest first.
 *
 * @param int $limit -1 for all.
 */
function bod_all_issues( $limit = -1 ) {
	$posts = get_posts(
		array(
			'post_type'      => 'bod_issue',
			'posts_per_page' => $limit,
			'post_status'    => 'publish',
			'meta_key'       => 'bod_sort_key', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key
			'orderby'        => 'meta_value_num',
			'order'          => 'DESC',
		)
	);

	return array_values( array_filter( array_map( 'bod_issue_data', $posts ) ) );
}

/**
 * Technology slugs that have earned a page — the WordPress twin of
 * db.mjs keptTagSlugs().
 */
function bod_linkable_tag_slugs() {
	static $cache = null;
	if ( null !== $cache ) {
		return $cache;
	}

	$terms = get_terms(
		array(
			'taxonomy'   => 'bod_tech',
			'hide_empty' => true,
		)
	);

	$cache = array();
	if ( ! is_wp_error( $terms ) ) {
		foreach ( $terms as $term ) {
			if ( bod_tech_is_public( $term ) ) {
				$cache[ $term->slug ] = true;
			}
		}
	}
	return $cache;
}

/** All technology terms above the threshold, most-used first. */
function bod_public_tech_terms() {
	$terms = get_terms(
		array(
			'taxonomy'   => 'bod_tech',
			'hide_empty' => true,
			'orderby'    => 'count',
			'order'      => 'DESC',
		)
	);
	if ( is_wp_error( $terms ) ) {
		return array();
	}
	return array_values( array_filter( $terms, 'bod_tech_is_public' ) );
}

/** Beat terms in editorial order, skipping empty ones. */
function bod_public_beat_terms() {
	$out = array();
	foreach ( array_keys( bod_beats() ) as $slug ) {
		$term = get_term_by( 'slug', $slug, 'bod_beat' );
		if ( $term && ! is_wp_error( $term ) && $term->count > 0 ) {
			$out[] = $term;
		}
	}
	return $out;
}

/** Total published stories of kind 'article', for the hero counter. */
function bod_total_articles() {
	$q = new WP_Query(
		array(
			'post_type'      => 'bod_story',
			'post_status'    => 'publish',
			'posts_per_page' => 1,
			'fields'         => 'ids',
			'no_found_rows'  => false,
			'meta_query'     => array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query
				array(
					'key'   => 'bod_kind',
					'value' => 'article',
				),
			),
		)
	);
	return (int) $q->found_posts;
}

/**
 * Group issues into year -> month buckets, newest first (port of
 * build.py _group_weeks_by_year_month).
 *
 * @param array $issues Output of bod_all_issues().
 */
function bod_group_issues_by_year_month( $issues ) {
	$years = array();

	foreach ( $issues as $issue ) {
		$year  = $issue['year'];
		$month = $issue['month'] ? $issue['month'] : 1;

		if ( ! isset( $years[ $year ] ) ) {
			$years[ $year ] = array(
				'year'   => $year,
				'count'  => 0,
				'months' => array(),
			);
		}
		$years[ $year ]['count']++;

		if ( ! isset( $years[ $year ]['months'][ $month ] ) ) {
			$years[ $year ]['months'][ $month ] = array(
				'month'      => $month,
				'month_name' => $issue['month_name'],
				'weeks'      => array(),
			);
		}
		$years[ $year ]['months'][ $month ]['weeks'][] = $issue;
	}

	krsort( $years );
	foreach ( $years as $year => $group ) {
		krsort( $years[ $year ]['months'] );
		$years[ $year ]['months'] = array_values( $years[ $year ]['months'] );
	}

	return array_values( $years );
}

/**
 * Stories carrying a given term, grouped by issue newest-first — the data
 * behind both the topic hub and the tag page.
 *
 * @param string $taxonomy 'bod_beat' or 'bod_tech'.
 * @param string $slug     Term slug.
 */
function bod_collection_groups( $taxonomy, $slug ) {
	$posts = get_posts(
		array(
			'post_type'      => 'bod_story',
			'posts_per_page' => -1,
			'post_status'    => 'publish',
			'meta_key'       => 'bod_sort_key', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key
			'orderby'        => array( 'meta_value_num' => 'DESC', 'menu_order' => 'ASC' ),
			'tax_query'      => array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query
				array(
					'taxonomy' => $taxonomy,
					'field'    => 'slug',
					'terms'    => $slug,
				),
			),
		)
	);

	$groups = array();
	$flat   = array();

	foreach ( $posts as $post ) {
		$issue = bod_issue_data( $post->post_parent );
		if ( ! $issue ) {
			continue;
		}
		$key = $issue['href'];
		if ( ! isset( $groups[ $key ] ) ) {
			$groups[ $key ] = array(
				'label'     => $issue['label'],
				'week_href' => $issue['href'],
				'entries'   => array(),
			);
		}

		$story              = bod_story_data( $post );
		$story['week_href'] = $issue['href'];
		$story['date']      = $issue['source_mtime'] ? gmdate( 'Y-m-d', (int) $issue['source_mtime'] ) : '';

		$groups[ $key ]['entries'][] = $story;
		$flat[]                      = $story;
	}

	return array(
		'groups' => array_values( $groups ),
		'flat'   => $flat,
		'count'  => count( $flat ),
	);
}
