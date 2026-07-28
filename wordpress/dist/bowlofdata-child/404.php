<?php
/**
 * 404. Reached by unknown URLs and by technology terms below the
 * BOD_MIN_TAG_ITEMS threshold (see inc/content.php).
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

bod_page_context(
	array(
		'title'        => 'Not found · ' . BOD_SITE_NAME,
		'description'  => 'That page does not exist. Browse the archive for every past issue.',
		'canonical'    => bod_canonical( '/archive.html' ),
		'current_page' => null,
	)
);

get_header();
?>
<div class="collection-header">
  <div class="collection-header-inner">
    <p class="collection-kicker">404</p>
    <h1 class="collection-title">Nothing served here</h1>
    <p class="collection-intro">
      That page does not exist — it may have moved, or never existed. Every issue we
      have published is in the archive.
    </p>
    <div class="collection-chips">
      <a href="<?php echo esc_url( bod_url( '/archive.html' ) ); ?>" class="chip chip--beat">Browse the archive</a>
      <a href="<?php echo esc_url( bod_url( '/topics.html' ) ); ?>" class="chip">All topics</a>
      <a href="<?php echo esc_url( bod_url( '/' ) ); ?>" class="chip">Home</a>
    </div>
  </div>
</div>
<?php
echo bod_subscribe_cta( '404' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
get_footer();
