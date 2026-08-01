<?php
/**
 * Generic fallback template.
 *
 * Nothing on bowlofdata.net routes here — every real URL has a dedicated
 * template (front-page, page-*, single-bod_issue, taxonomy-*, 404). This exists
 * so that untemplated content does not render Blocksy's body markup inside our
 * shell. Note that this file is not reached by the template hierarchy alone:
 * the parent supplies page.php and singular.php, which outrank it. The
 * template_include filter in functions.php is what routes here.
 *
 * What lands here is leftover WordPress content with no .net twin, so it gets
 * no canonical (see bod_page_context()) and is marked noindex (see inc/seo.php).
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$bod_heading = single_post_title( '', false );
if ( ! $bod_heading ) {
	$bod_heading = BOD_SITE_NAME;
}

bod_page_context(
	array(
		'title'       => $bod_heading . ' · ' . BOD_SITE_NAME,
		'description' => BOD_SITE_TAGLINE,
	)
);

get_header();
?>
<div class="collection-header">
  <div class="collection-header-inner">
    <h1 class="collection-title"><?php echo bod_esc( $bod_heading ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- pre-escaped by bod_esc(). ?></h1>
    <div class="collection-chips">
      <a href="<?php echo esc_url( bod_url( '/archive.html' ) ); ?>" class="chip chip--beat">Browse the archive</a>
      <a href="<?php echo esc_url( bod_url( '/topics.html' ) ); ?>" class="chip">All topics</a>
      <a href="<?php echo esc_url( bod_url( '/' ) ); ?>" class="chip">Home</a>
    </div>
  </div>
</div>

<?php
while ( have_posts() ) :
	the_post();
	$bod_body = get_the_content();
	if ( '' === trim( wp_strip_all_tags( $bod_body ) ) ) {
		continue;
	}
	?>
<div class="collection-body">
  <div class="article-body">
    <?php echo wp_kses_post( apply_filters( 'the_content', $bod_body ) ); ?>
  </div>
</div>
	<?php
endwhile;

echo bod_subscribe_cta( 'fallback' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- markup from bod_subscribe_cta().
get_footer();
