<?php
/**
 * Topic hub — /topic/ai.html
 *
 * Port of topic.mjs + renderCollection(). Related-tag chips are the top 12
 * technologies seen on this beat that clear the ≥3 threshold.
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$term = get_queried_object();
if ( ! $term instanceof WP_Term ) {
	status_header( 404 );
	include get_query_template( '404' );
	return;
}

$collection = bod_collection_groups( 'bod_beat', $term->slug );
if ( ! $collection['count'] ) {
	status_header( 404 );
	include get_query_template( '404' );
	return;
}

$beats = bod_beats();
$meta  = isset( $beats[ $term->slug ] ) ? $beats[ $term->slug ] : array(
	'label' => $term->name,
	'h1'    => $term->name,
	'intro' => '',
);

// Top technologies co-occurring with this beat.
$tag_counts = array();
foreach ( $collection['flat'] as $story ) {
	$terms = get_the_terms( $story['id'], 'bod_tech' );
	if ( ! is_array( $terms ) ) {
		continue;
	}
	foreach ( $terms as $t ) {
		if ( ! bod_tech_is_public( $t ) ) {
			continue;
		}
		if ( ! isset( $tag_counts[ $t->slug ] ) ) {
			$tag_counts[ $t->slug ] = array(
				'slug'  => $t->slug,
				'name'  => $t->name,
				'count' => 0,
			);
		}
		$tag_counts[ $t->slug ]['count']++;
	}
}
usort(
	$tag_counts,
	static function ( $a, $b ) {
		return $b['count'] <=> $a['count'];
	}
);
$related_tags = array_slice( array_values( $tag_counts ), 0, 12 );

$canonical = bod_canonical( '/topic/' . $term->slug . '.html' );
$og_desc   = $meta['intro'];

bod_page_context(
	array(
		'title'        => $meta['h1'] . ' · ' . BOD_SITE_NAME,
		'description'  => $og_desc,
		'og_type'      => 'article',
		'canonical'    => $canonical,
		'current_page' => 'topics',
		'jsonld'       => array(
			bod_collection_jsonld( $meta['h1'] . ' · ' . BOD_SITE_NAME, $og_desc, $canonical, $collection['flat'] ),
			bod_breadcrumb_jsonld(
				array(
					array( BOD_SITE_NAME, BOD_CANONICAL_ORIGIN . '/' ),
					array( 'Topics', BOD_CANONICAL_ORIGIN . '/topics.html' ),
					array( $meta['h1'], $canonical ),
				)
			),
		),
	)
);

get_header();

echo bod_render_collection_body( // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside.
	array(
		'kicker'       => 'Topic',
		'h1'           => $meta['h1'],
		'intro'        => $meta['intro'],
		'count'        => $collection['count'],
		'groups'       => $collection['groups'],
		'related_tags' => $related_tags,
	)
);

get_footer();
