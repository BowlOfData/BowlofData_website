<?php
/**
 * Topics & tags index — /topics.html
 *
 * Port of templates/topics.html. Beat counts come from the taxonomy; the tag
 * cloud shows only technologies past BOD_MIN_TAG_ITEMS.
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$beats_meta = bod_beats();
$hubs       = bod_public_beat_terms();
$tags       = bod_public_tech_terms();

bod_page_context(
	array(
		'title'        => 'Topics & Tags · ' . BOD_SITE_NAME,
		'description'  => 'Browse Bowl of Data by topic — AI, cybersecurity, blockchain, and software engineering — and by technology tag across every weekly issue.',
		'og_type'      => 'website',
		'canonical'    => bod_canonical( '/topics.html' ),
		'current_page' => 'topics',
		'jsonld'       => array(
			bod_breadcrumb_jsonld(
				array(
					array( BOD_SITE_NAME, BOD_CANONICAL_ORIGIN . '/' ),
					array( 'Topics', BOD_CANONICAL_ORIGIN . '/topics.html' ),
				)
			),
		),
	)
);

get_header();
?>
<div class="collection-header">
  <div class="collection-header-inner">
    <p class="collection-kicker">Browse</p>
    <h1 class="collection-title">Topics &amp; tags</h1>
    <p class="collection-intro">
      Every issue of Bowl of Data, reorganised by beat and by technology — the fast way into
      our weekly coverage of AI, cybersecurity, blockchain, and software engineering.
    </p>
  </div>
</div>

<section class="band">
  <div class="band-inner">
    <div class="band-head">
      <h2 class="band-title">By topic</h2>
      <span class="eyebrow">Four beats</span>
    </div>
    <div class="cov">
<?php foreach ( $hubs as $hub ) : ?>
<?php $meta = isset( $beats_meta[ $hub->slug ] ) ? $beats_meta[ $hub->slug ] : array( 'label' => $hub->name, 'h1' => $hub->name ); ?>
      <a class="cov-item cov-<?php echo esc_attr( $hub->slug ); ?>" href="<?php echo esc_url( bod_url( '/topic/' . $hub->slug . '.html' ) ); ?>">
        <p class="cov-k"><?php echo esc_html( $meta['label'] ); ?></p>
        <h3 class="cov-n"><?php echo esc_html( $meta['h1'] ); ?></h3>
        <p class="cov-d"><?php echo (int) $hub->count; ?> curated item<?php echo esc_html( bod_plural( $hub->count ) ); ?> across every issue →</p>
      </a>
<?php endforeach; ?>
    </div>
  </div>
</section>

<?php if ( $tags ) : ?>
<section class="band">
  <div class="band-inner">
    <div class="band-head">
      <h2 class="band-title">By technology</h2>
      <span class="eyebrow"><?php echo count( $tags ); ?> tags</span>
    </div>
    <div class="tag-cloud">
<?php foreach ( $tags as $tag ) : ?>
      <a href="<?php echo esc_url( bod_url( '/tag/' . $tag->slug . '.html' ) ); ?>" class="chip chip--lg"><?php echo esc_html( $tag->name ); ?> <span><?php echo (int) $tag->count; ?></span></a>
<?php endforeach; ?>
    </div>
  </div>
</section>
<?php endif; ?>
<?php
echo bod_subscribe_cta( 'topics' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
get_footer();
