(() => {
  "use strict";

  if (window.location.protocol !== "file:") return;

  const currentPath = window.location.pathname.replace(/\\/g, "/");
  const repositoryMarker = "/akira-l.github.io/";
  const previewMarker = "/.preview-site/";
  const repositoryIndex = currentPath.indexOf(repositoryMarker);
  const previewIndex = currentPath.indexOf(previewMarker);
  if (repositoryIndex < 0) return;

  const publicRootPath = currentPath.slice(
    0,
    repositoryIndex + repositoryMarker.length
  );
  const inPreview = previewIndex >= 0;
  const previewRootPath = inPreview
    ? currentPath.slice(0, previewIndex + previewMarker.length)
    : `${publicRootPath}.preview-site/`;
  const currentRootPath = inPreview ? previewRootPath : publicRootPath;
  const publicRoot = new URL(`file://${publicRootPath}`);
  const previewRoot = new URL(`file://${previewRootPath}`);
  const currentRelativePath = currentPath.slice(currentRootPath.length);
  const localOrigin = "https://local-preview.invalid";
  const productionOrigin = "https://akira-l.github.io";
  const currentRoute = new URL(
    currentRelativePath || "index.html",
    `${localOrigin}/`
  );

  const isReviewRoute = (path) =>
    path.startsWith("research/") ||
    path.startsWith("zh/research/") ||
    path.startsWith("research-notes/");

  document.querySelectorAll("a[href]").forEach((anchor) => {
    const rawHref = anchor.getAttribute("href");
    if (
      !rawHref ||
      rawHref.startsWith("#") ||
      rawHref.startsWith("//") ||
      /^(mailto|tel|javascript|data):/i.test(rawHref)
    ) {
      return;
    }

    let route;
    try {
      if (/^[a-z][a-z0-9+.-]*:/i.test(rawHref)) {
        const absolute = new URL(rawHref);
        if (absolute.origin !== productionOrigin) return;
        route = new URL(
          `${absolute.pathname}${absolute.search}${absolute.hash}`,
          `${localOrigin}/`
        );
      } else if (rawHref.startsWith("/")) {
        route = new URL(rawHref, `${localOrigin}/`);
      } else {
        route = new URL(rawHref, currentRoute);
      }
    } catch (_error) {
      return;
    }

    if (route.origin !== localOrigin) return;
    let localPath = route.pathname.replace(/^\/+/, "");
    if (!localPath || localPath.endsWith("/")) localPath += "index.html";

    const targetRoot = inPreview || isReviewRoute(localPath)
      ? previewRoot
      : publicRoot;
    anchor.href = new URL(
      `${localPath}${route.search}${route.hash}`,
      targetRoot
    ).href;
  });

  document.querySelectorAll('link[rel="stylesheet"][href]').forEach((link) => {
    const rawHref = link.getAttribute("href");
    const match = rawHref && rawHref.match(/(?:^|\/)(dist\/[^?#]+)/);
    if (match) {
      link.href = new URL(match[1], inPreview ? previewRoot : publicRoot).href;
    }
  });

  document.querySelectorAll('[src^="/"]').forEach((element) => {
    const rawSource = element.getAttribute("src");
    if (rawSource) {
      element.setAttribute(
        "src",
        new URL(rawSource.replace(/^\/+/, ""), inPreview ? previewRoot : publicRoot)
          .href
      );
    }
  });
})();
