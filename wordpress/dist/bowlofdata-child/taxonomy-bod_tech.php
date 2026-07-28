<?php
/**
 * Technology tag page — /tag/python.html
 *
 * Port of tag.mjs + renderCollection(). Terms below BOD_MIN_TAG_ITEMS never
 * reach this template: inc/content.php 404s them on template_redirect.
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

$collection = bod_collection_groups( 'bod_tech', $term->slug );
if ( $collection['count'] < BOD_MIN_TAG_ITEMS ) {
	status_header( 404 );
	include get_query_template( '404' );
	return;
}

// Beats this technology shows up in, in editorial order.
$beats          = bod_beats();
$seen           = array();
$related_topics = array();
foreach ( $collection['flat'] as $story ) {
	if ( $story['category'] && ! isset( $seen[ $story['category'] ] ) ) {
		$seen[ $story['category'] ] = true;
	}
}
foreach ( array_keys( $beats ) as $slug ) {
	if ( isset( $seen[ $slug ] ) ) {
		$related_topics[] = array(
			'slug'  => $slug,
			'label' => $beats[ $slug ]['label'],
		);
	}
}

$canonical = bod_canonical( '/tag/' . $term->slug . '.html' );
$intro     = sprintf(
	'Every %s story Bowl of Data has covered — newest first, with the issue each one appeared in.',
	$term->name
);

bod_page_context(
	array(
		'title'        => $term->name . ' · ' . BOD_SITE_NAME,
		'description'  => $intro,
		'og_type'      => 'article',
		'canonical'    => $canonical,
		'current_page' => 'topics',
		'jsonld'       => array(
			bod_collection_jsonld( $term->name . ' · ' . BOD_SITE_NAME, $intro, $canonical, $collection['flat'] ),
			bod_breadcrumb_jsonld(
				array(
					array( BOD_SITE_NAME, BOD_CANONICAL_ORIGIN . '/' ),
					array( 'Topics', BOD_CANONICAL_ORIGIN . '/topics.html' ),
					array( $term->name, $canonical ),
				)
			),
		),
	)
);

get_header();

echo bod_render_collection_body( // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside.
	array(
		'kicker'         => 'Tag',
		'h1'             => $term->name,
		'intro'          => $intro,
		'count'          => $collection['count'],
		'groups'         => $collection['groups'],
		'related_topics' => $related_topics,
	)
);

get_footer();
