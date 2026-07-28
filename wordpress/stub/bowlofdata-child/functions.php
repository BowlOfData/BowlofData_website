<?php
/**
 * Bowl of Data child theme — Phase 0 upload-gate stub.
 *
 * Does nothing except load the parent (Blocksy) stylesheet followed by the
 * child's own, which is the minimum a valid child theme must do. The real
 * theme replaces this file wholesale in Phase 1.
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

add_action(
	'wp_enqueue_scripts',
	static function () {
		wp_enqueue_style(
			'bowlofdata-parent',
			get_template_directory_uri() . '/style.css',
			array(),
			wp_get_theme( get_template() )->get( 'Version' )
		);

		wp_enqueue_style(
			'bowlofdata-child',
			get_stylesheet_uri(),
			array( 'bowlofdata-parent' ),
			wp_get_theme()->get( 'Version' )
		);
	}
);
