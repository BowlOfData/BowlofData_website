<?php
/**
 * Contact form handling.
 *
 * The plan called for Contact Form 7, but CF7 stores its forms in a CPT that
 * is not exposed over REST, so wiring it up would have meant a second manual
 * wp-admin step AND rebuilding our markup inside CF7's form editor — losing the
 * exact classes templates/contact.html uses. Handling the post here keeps the
 * markup identical and the migration fully scripted.
 *
 * Every submission is stored as a private bod_message post as well as emailed,
 * so nothing is lost if wp_mail() is unreliable on Altervista's free plan.
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

add_action(
	'init',
	static function () {
		register_post_type(
			'bod_message',
			array(
				'labels'       => array(
					'name'          => __( 'Messages', 'bowlofdata' ),
					'singular_name' => __( 'Message', 'bowlofdata' ),
				),
				'public'       => false,
				'show_ui'      => true,
				'show_in_menu' => true,
				'show_in_rest' => false,
				'capabilities' => array( 'create_posts' => 'do_not_allow' ),
				'map_meta_cap' => true,
				'menu_icon'    => 'dashicons-email',
				'supports'     => array( 'title', 'editor', 'custom-fields' ),
			)
		);
	},
	6
);

add_action( 'wp_ajax_bod_contact', 'bod_handle_contact' );
add_action( 'wp_ajax_nopriv_bod_contact', 'bod_handle_contact' );

/** Receive a contact submission and reply with JSON for the inline fetch(). */
function bod_handle_contact() {
	check_ajax_referer( 'bod_contact', 'bod_nonce' );

	// Honeypot: bots fill hidden fields, humans never see this one.
	if ( ! empty( $_POST['bot-field'] ) ) {
		wp_send_json_success( array( 'ok' => true ) );
	}

	$name    = sanitize_text_field( wp_unslash( $_POST['name'] ?? '' ) );
	$email   = sanitize_email( wp_unslash( $_POST['email'] ?? '' ) );
	$subject = sanitize_text_field( wp_unslash( $_POST['subject'] ?? 'other' ) );
	$message = sanitize_textarea_field( wp_unslash( $_POST['message'] ?? '' ) );

	if ( ! $name || ! is_email( $email ) || ! $message ) {
		wp_send_json_error( array( 'message' => 'Please fill in your name, a valid email, and a message.' ), 400 );
	}

	$allowed = array( 'feedback', 'article-suggestion', 'partnership', 'other' );
	if ( ! in_array( $subject, $allowed, true ) ) {
		$subject = 'other';
	}

	$post_id = wp_insert_post(
		array(
			'post_type'    => 'bod_message',
			'post_status'  => 'private',
			'post_title'   => sprintf( '[%s] %s', $subject, $name ),
			'post_content' => $message,
			'meta_input'   => array(
				'bod_from_name'  => $name,
				'bod_from_email' => $email,
				'bod_subject'    => $subject,
			),
		),
		true
	);

	if ( is_wp_error( $post_id ) ) {
		wp_send_json_error( array( 'message' => 'Could not save your message.' ), 500 );
	}

	// Best-effort notification. A failure here is not a failure for the sender:
	// the message is already stored.
	wp_mail(
		get_option( 'admin_email' ),
		sprintf( '[%s] Contact form: %s', BOD_SITE_NAME, $subject ),
		sprintf( "From: %s <%s>\nSubject: %s\n\n%s\n", $name, $email, $subject, $message ),
		array( 'Reply-To: ' . $name . ' <' . $email . '>' )
	);

	wp_send_json_success( array( 'ok' => true ) );
}
