<?php
/**
 * The document head, site header and opening <main>.
 *
 * Port of shell() in netlify/functions/_shared/render.mjs (lines 346-400) and
 * of templates/base.html lines 1-81. Templates call bod_page_context() with
 * their title/description/canonical/JSON-LD before get_header().
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$bod_ctx     = bod_page_context();
$bod_title   = bod_esc( $bod_ctx['title'] );
$bod_desc    = bod_esc( $bod_ctx['description'] );
$bod_url     = bod_esc( $bod_ctx['canonical'] );
$bod_origin  = BOD_CANONICAL_ORIGIN;
$bod_current = $bod_ctx['current_page'];

/** aria-current="page" for the active nav item. */
$bod_cur = static function ( $page ) use ( $bod_current ) {
	return $bod_current === $page ? 'aria-current="page"' : '';
};
$bod_about_active = in_array( $bod_current, array( 'about', 'team', 'contact' ), true ) ? 'data-active="true"' : '';
?><!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
  <meta charset="<?php bloginfo( 'charset' ); ?>">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?php echo $bod_title; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- pre-escaped by bod_esc(). ?></title>
  <meta name="description" content="<?php echo $bod_desc; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>">
  <meta name="author" content="<?php echo bod_esc( BOD_SITE_NAME ); ?> team">
  <link rel="canonical" href="<?php echo $bod_url; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>">
  <link rel="icon" type="image/png" href="<?php echo esc_url( $bod_origin . '/imgs/logo.png' ); ?>">
  <link rel="apple-touch-icon" href="<?php echo esc_url( $bod_origin . '/imgs/logo.png' ); ?>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <!-- Open Graph -->
  <meta property="og:site_name" content="<?php echo bod_esc( BOD_SITE_NAME ); ?>">
  <meta property="og:type" content="<?php echo bod_esc( $bod_ctx['og_type'] ); ?>">
  <meta property="og:title" content="<?php echo $bod_title; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>">
  <meta property="og:description" content="<?php echo $bod_desc; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>">
  <meta property="og:image" content="<?php echo esc_url( $bod_origin . '/imgs/bowl.png' ); ?>">
  <meta property="og:image:width" content="2560">
  <meta property="og:image:height" content="1440">
  <meta property="og:image:alt" content="<?php echo bod_esc( BOD_SITE_NAME ); ?> — weekly tech newsletter">
  <meta property="og:url" content="<?php echo $bod_url; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>">
  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="<?php echo $bod_title; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>">
  <meta name="twitter:description" content="<?php echo $bod_desc; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>">
  <meta name="twitter:image" content="<?php echo esc_url( $bod_origin . '/imgs/bowl.png' ); ?>">
  <link rel="alternate" type="application/rss+xml" title="<?php echo bod_esc( BOD_SITE_NAME ); ?> RSS Feed" href="<?php echo esc_url( $bod_origin . '/feed.xml' ); ?>">
  <script type="application/ld+json"><?php echo bod_organization_jsonld(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON. ?></script>
<?php foreach ( $bod_ctx['jsonld'] as $bod_block ) : ?>
  <script type="application/ld+json"><?php echo $bod_block; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON. ?></script>
<?php endforeach; ?>
<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>

  <header class="site-header">
    <div class="header-inner">
      <a href="<?php echo esc_url( bod_url( '/' ) ); ?>" class="header-brand">
        <img src="<?php echo esc_url( get_stylesheet_directory_uri() . '/imgs/logo.png' ); ?>" alt="<?php echo bod_esc( BOD_SITE_NAME ); ?> logo" class="header-logo">
        <div class="header-text">
          <span class="header-site-name"><?php echo bod_esc( BOD_SITE_NAME ); ?></span>
          <span class="header-tagline"><?php echo bod_esc( BOD_SITE_TAGLINE ); ?></span>
        </div>
      </a>
      <button class="menu-toggle" aria-label="Toggle navigation" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
      <nav class="header-nav">
        <a href="<?php echo esc_url( bod_url( '/' ) ); ?>" class="nav-link" <?php echo $bod_cur( 'home' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>>Home</a>
        <a href="<?php echo esc_url( bod_url( '/archive.html' ) ); ?>" class="nav-link" <?php echo $bod_cur( 'archive' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>>Archive</a>
        <a href="<?php echo esc_url( bod_url( '/topics.html' ) ); ?>" class="nav-link" <?php echo $bod_cur( 'topics' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>>Topics</a>
        <a href="<?php echo esc_url( bod_url( '/services.html' ) ); ?>" class="nav-link nav-link--services" <?php echo $bod_cur( 'services' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>>Services</a>
        <div class="nav-more-group">
          <button class="nav-more-btn" aria-expanded="false" aria-haspopup="true" <?php echo $bod_about_active; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>>
            About
            <svg class="nav-more-chevron" width="10" height="6" viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 1l4 4 4-4"/></svg>
          </button>
          <div class="nav-more-panel">
            <a href="<?php echo esc_url( bod_url( '/about.html' ) ); ?>" class="nav-link" <?php echo $bod_cur( 'about' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>>About</a>
            <a href="<?php echo esc_url( bod_url( '/team.html' ) ); ?>" class="nav-link" <?php echo $bod_cur( 'team' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>>Team</a>
            <a href="<?php echo esc_url( bod_url( '/contact.html' ) ); ?>" class="nav-link" <?php echo $bod_cur( 'contact' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>>Contact</a>
            <a href="<?php echo esc_url( BOD_PODCAST_URL ); ?>" class="nav-link nav-link--podcast" target="_blank" rel="noopener">
              <svg class="nav-podcast-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141 4.32-1.32 9.719-.66 13.5 1.62.32.24.5.72.24 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.6.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z"/>
              </svg>
              Podcast
            </a>
          </div>
        </div>
        <a href="<?php echo esc_url( BOD_SUBSTACK_URL ); ?>" class="nav-subscribe" target="_blank" rel="noopener">Subscribe</a>
      </nav>
    </div>
  </header>

  <main class="main-content">
