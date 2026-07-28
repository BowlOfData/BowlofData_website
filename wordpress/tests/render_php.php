<?php
/**
 * Render the shared fixture through the theme's PHP port, with just enough
 * WordPress stubbed to load inc/render.php standalone. Paired with
 * render_js.mjs by parity.sh.
 */

define( 'ABSPATH', __DIR__ );
define( 'BOD_SITE_NAME', 'Bowl of Data' );
define( 'BOD_SITE_TAGLINE', 'A weekly digest of the most relevant tech stories' );
define( 'BOD_CANONICAL_ORIGIN', 'https://bowlofdata.net' );
define( 'BOD_PODCAST_URL', 'https://open.spotify.com/show/033Mqus9YAIssepHakRIIk' );
define( 'BOD_SUBSTACK_URL', 'https://bowlofdata.substack.com/' );

// --- WordPress stubs -------------------------------------------------------

function esc_url( $url ) {
	return str_replace( array( '&', "'", '"' ), array( '&amp;', '&#039;', '&quot;' ), $url );
}
function esc_html( $s ) {
	return htmlspecialchars( (string) $s, ENT_QUOTES );
}
function esc_attr( $s ) {
	return htmlspecialchars( (string) $s, ENT_QUOTES );
}
function wp_json_encode( $data, $flags = 0 ) {
	return json_encode( $data, $flags );
}
function home_url( $path = '/' ) {
	return 'https://bowlofdata.altervista.org' . $path;
}
function wp_parse_args( $args, $defaults ) {
	return array_merge( $defaults, $args );
}

require __DIR__ . '/../bowlofdata-child/inc/render.php';

$article  = json_decode( file_get_contents( __DIR__ . '/fixture-article.json' ), true );
$linkable = array(
	'openai' => true,
	'rust'   => true,
);

echo bod_article_card( $article, 1, 'Article', 'Read full article', $linkable );
