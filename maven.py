"""Utilities for downloading artifacts from Maven repositories."""

import dataclasses
import pathlib
import urllib.error
import urllib.request
import warnings
import xml.etree.ElementTree as ET
import zipfile

# Repositories tried in order; first successful download wins.
MAVEN_REPOSITORIES = [
    "https://dl.google.com/dl/android/maven2",  # Google Maven (androidx, com.android, …)
    "https://repo1.maven.org/maven2",            # Maven Central
]


def _artifact_url(repository: str, group_id: str, artifact_id: str, version: str, extension: str) -> str:
    group_path = group_id.replace(".", "/")
    filename = f"{artifact_id}-{version}.{extension}"
    return f"{repository}/{group_path}/{artifact_id}/{version}/{filename}"


def download_maven_artifact(
    package: str,
    output_dir: str | pathlib.Path = ".",
    repositories: list[str] | None = None,
) -> pathlib.Path:
    """Download a Maven artifact (``.aar`` or ``.jar``) to *output_dir*.

    Tries to download the ``.aar`` first; if none is found in any repository,
    falls back to ``.jar``.

    Parameters
    ----------
    package:
        Maven package in the form ``"groupId:artifactId:version"``,
        e.g. ``"androidx.appcompat:appcompat:1.0.2"``.
    output_dir:
        Directory where the artifact file will be saved.  Defaults to the
        current working directory.
    repositories:
        List of Maven repository base URLs to try, in order.  Defaults to
        :data:`MAVEN_REPOSITORIES`.

    Returns
    -------
    pathlib.Path
        Path to the downloaded ``.aar`` or ``.jar`` file.

    Raises
    ------
    ValueError
        If *package* is not in the expected ``groupId:artifactId:version``
        format.
    FileNotFoundError
        If the artifact could not be found as ``.aar`` or ``.jar`` in any
        of the repositories.

    Example
    -------
    >>> import pathlib, tempfile
    >>> # (network call omitted in doctests)
    """
    parts = package.strip().split(":")
    if len(parts) != 3:
        raise ValueError(
            f"Invalid Maven package {package!r}. "
            "Expected format: 'groupId:artifactId:version'"
        )
    group_id, artifact_id, version = parts

    if repositories is None:
        repositories = MAVEN_REPOSITORIES

    output_path = pathlib.Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    all_errors: list[str] = []
    for extension in ("aar", "jar"):
        dest = output_path / f"{artifact_id}-{version}.{extension}"
        errors: list[str] = []
        for repo in repositories:
            url = _artifact_url(repo, group_id, artifact_id, version, extension)
            try:
                with urllib.request.urlopen(url) as response:
                    dest.write_bytes(response.read())
                return dest
            except urllib.error.HTTPError as e:
                errors.append(f"{url} -> HTTP {e.code}")
            except urllib.error.URLError as e:
                errors.append(f"{url} -> {e.reason}")
        all_errors.extend(errors)

    raise FileNotFoundError(
        f"Could not download {package!r} (.aar or .jar) from any repository:\n"
        + "\n".join(f"  {e}" for e in all_errors)
    )


def extract_aar(
    aar_path: str | pathlib.Path,
    output_dir: str | pathlib.Path | None = None,
) -> pathlib.Path:
    """Extract a ``.aar`` archive.

    An ``.aar`` is a ZIP archive with the following relevant contents:

    * ``classes.jar``   — the compiled Java classes
    * ``libs/*.jar``    — additional JARs bundled with the library
    * ``res/``          — Android resources
    * ``AndroidManifest.xml``, ``R.txt``, …

    Parameters
    ----------
    aar_path:
        Path to the ``.aar`` file to extract.
    output_dir:
        Directory where the contents will be extracted.  Defaults to a
        directory next to the ``.aar`` file with the same stem
        (e.g. ``appcompat-1.0.2/`` for ``appcompat-1.0.2.aar``).

    Returns
    -------
    pathlib.Path
        Path to the directory the archive was extracted into.
    """
    aar_path = pathlib.Path(aar_path)
    if output_dir is None:
        output_dir = aar_path.parent / aar_path.stem
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(aar_path) as zf:
        zf.extractall(output_dir)

    return output_dir

def get_jars_from_aar(aar_dir: str | pathlib.Path) -> list[pathlib.Path]:
    """Return all JAR files contained in an extracted ``.aar`` directory.

    This includes ``classes.jar`` (if present) and any JARs under ``libs/``.

    Parameters
    ----------
    aar_dir:
        Path to the directory produced by :func:`extract_aar`.

    Returns
    -------
    list[pathlib.Path]
        List of JAR file paths, ``classes.jar`` first (if present).
    """
    aar_dir = pathlib.Path(aar_dir)
    jars: list[pathlib.Path] = []

    classes_jar = aar_dir / "classes.jar"
    if classes_jar.exists():
        jars.append(classes_jar)

    jars.extend(sorted((aar_dir / "libs").glob("*.jar")) if (aar_dir / "libs").is_dir() else [])

    return jars



def fetch_maven_pom_dependencies(
    package: str,
    repositories: list[str] | None = None,
) -> list[str]:
    """Fetch the direct runtime dependencies of a Maven artifact by reading its POM file.

    The POM is a small XML file published alongside every artifact on Maven
    repositories — no download of the ``.aar`` / ``.jar`` is required.

    Only ``compile`` and ``runtime`` scoped dependencies are included;
    ``test``, ``provided`` and optional dependencies are skipped.

    Parameters
    ----------
    package:
        Maven package in the form ``"groupId:artifactId:version"``.
    repositories:
        List of Maven repository base URLs to try, in order.  Defaults to
        :data:`MAVEN_REPOSITORIES`.

    Returns
    -------
    list[str]
        Direct dependency coordinates in ``"groupId:artifactId:version"`` format.

    Raises
    ------
    FileNotFoundError
        If the POM could not be found in any repository.
    """
    parts = package.strip().split(":")
    if len(parts) != 3:
        raise ValueError(
            f"Invalid Maven package {package!r}. "
            "Expected format: 'groupId:artifactId:version'"
        )
    group_id, artifact_id, version = parts

    if repositories is None:
        repositories = MAVEN_REPOSITORIES

    errors: list[str] = []
    pom_xml: str | None = None
    for repo in repositories:
        url = _artifact_url(repo, group_id, artifact_id, version, "pom")
        try:
            with urllib.request.urlopen(url) as response:
                pom_xml = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as e:
            errors.append(f"{url} -> HTTP {e.code}")
        except urllib.error.URLError as e:
            errors.append(f"{url} -> {e.reason}")

    if pom_xml is None:
        raise FileNotFoundError(
            f"Could not download POM for {package!r}:\n"
            + "\n".join(f"  {e}" for e in errors)
        )

    # POM files use a namespace, e.g. xmlns="http://maven.apache.org/POM/4.0.0"
    root = ET.fromstring(pom_xml)
    ns = root.tag[: root.tag.index("}") + 1] if "}" in root.tag else ""

    dependencies: list[str] = []
    for dep in root.findall(f".//{ns}dependency"):
        dep_group = (dep.findtext(f"{ns}groupId") or "").strip()
        dep_artifact = (dep.findtext(f"{ns}artifactId") or "").strip()
        dep_version = (dep.findtext(f"{ns}version") or "").strip()
        dep_scope = (dep.findtext(f"{ns}scope") or "compile").strip()
        dep_optional = (dep.findtext(f"{ns}optional") or "false").strip().lower()

        if dep_optional == "true":
            continue
        if dep_scope not in {"compile", "runtime"}:
            continue
        if not dep_version or dep_version.startswith("$"):
            warnings.warn(
                f"Skipping {dep_group}:{dep_artifact} in {package!r}: "
                "version not pinned (managed via BOM/dependencyManagement).",
                stacklevel=2,
            )
            continue

        dependencies.append(f"{dep_group}:{dep_artifact}:{dep_version}")

    return dependencies


@dataclasses.dataclass
class MavenDependencyNode:
    """A node in a Maven dependency tree.

    Attributes
    ----------
    package:
        The Maven package in ``"groupId:artifactId:version"`` format.
    dependencies:
        Direct (compile/runtime) dependencies, each as a :class:`MavenDependencyNode`.
    pom_error:
        If the POM could not be fetched, the error message is stored here
        and ``dependencies`` will be empty.
    """

    package: str
    dependencies: list["MavenDependencyNode"] = dataclasses.field(default_factory=list)
    pom_error: str | None = None

    def all_packages(self) -> list[str]:
        """Return every package in the subtree (self included) in BFS order, without duplicates."""
        seen: set[str] = set()
        result: list[str] = []
        queue: list[MavenDependencyNode] = [self]
        while queue:
            node = queue.pop(0)
            if node.package not in seen:
                seen.add(node.package)
                result.append(node.package)
                queue.extend(node.dependencies)
        return result

    def print_tree(self, _indent: int = 0) -> None:
        """Print the dependency tree to stdout."""
        suffix = f"  [POM error: {self.pom_error}]" if self.pom_error else ""
        print("  " * _indent + self.package + suffix)
        for dep in self.dependencies:
            dep.print_tree(_indent + 1)


def resolve_dependency_tree(
    package: str,
    repositories: list[str] | None = None,
    _visited: set[str] | None = None,
) -> MavenDependencyNode:
    """Build the full transitive dependency tree for a Maven artifact.

    Only POM files are fetched — no ``.aar`` or ``.jar`` files are downloaded.
    Only ``compile`` and ``runtime`` scoped dependencies are included.
    Cycles and diamond dependencies are handled: each package is resolved
    only once; subsequent occurrences become childless leaf nodes.

    Parameters
    ----------
    package:
        Maven package in the form ``"groupId:artifactId:version"``.
    repositories:
        Maven repository base URLs to try, in order.  Defaults to
        :data:`MAVEN_REPOSITORIES`.

    Returns
    -------
    MavenDependencyNode
        Root node of the dependency tree.
    """
    import logging

    log = logging.getLogger(__name__)

    if _visited is None:
        _visited = set()

    # Mark as visited *before* recursing to break cycles.
    already_visited = package in _visited
    _visited.add(package)

    if already_visited:
        # Return a leaf — the full subtree is already represented elsewhere.
        return MavenDependencyNode(package=package)

    try:
        direct_deps = fetch_maven_pom_dependencies(package, repositories)
    except (FileNotFoundError, ValueError) as e:
        log.warning("Could not resolve POM for %s: %s", package, e)
        return MavenDependencyNode(package=package, pom_error=str(e))

    children = [
        resolve_dependency_tree(dep, repositories, _visited)
        for dep in direct_deps
    ]
    return MavenDependencyNode(package=package, dependencies=children)



if __name__ == "__main__":
    # aar = download_maven_aar("androidx.appcompat:appcompat:1.0.2", "./libs")
    # aar_dir = extract_aar(aar)
    # jars = get_jars_from_aar(aar_dir)

    # print(f"Downloaded {aar} and extracted {len(jars)} JAR(s):")
    # for jar in jars:
    #     print(f"  {jar}")

    tree = resolve_dependency_tree("androidx.appcompat:appcompat:1.0.2")
    tree.print_tree()

    packages = tree.all_packages()
    print("\nAll packages:")
    for pkg in packages:
        print(f"  {pkg}")

    # Erst nach Prüfung downloaden:
    all_jars: list[pathlib.Path] = []
    for pkg in tree.all_packages():
        file = download_maven_artifact(pkg, "./dist/libs")
        if file.suffix == ".aar":
            aar_dir = extract_aar(file)
            all_jars.extend(get_jars_from_aar(aar_dir))
        else:
            all_jars.append(file)

    print("\nAll JARs:")
    for jar in all_jars:
        print(f"  {jar}")
    print(":".join(str(jar) for jar in all_jars))
