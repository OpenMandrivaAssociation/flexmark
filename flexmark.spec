Name:		flexmark
Version:	0.34.60
Release:	1
Summary:	CommonMark parser and HTML renderer used by Gradle's documentation
Group:		Development/Java
License:	BSD-2-Clause
URL:		https://github.com/vsch/flexmark-java
# Maven Central sources jars for flexmark, flexmark-util, flexmark-formatter,
# flexmark-ext-anchorlink, and flexmark-ext-tables. The 0.34.60 git tag is gone.
Source0:	flexmark-%{version}.tar.gz
Patch0:		flexmark-0.34.60-entryset.patch

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem

%description
flexmark-java core, util, formatter, tables, and anchorlink at the
version Gradle 9.9.1 uses to render markdown. The catalog coordinate is
flexmark-all. Those five modules are what that renderer imports, and
they are packed into one jar so the coordinate does not pull the PDF,
DOCX, or autolink modules. ImageUtils is not compiled: it imports
sun.misc.BASE64Decoder, which this JDK does not provide, and nothing
else in this build references it.

%prep
%autosetup -n flexmark-%{version} -p1
find . \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -delete

%build
set -eo pipefail
find flexmark-util -name '*.java' ! -name 'ImageUtils.java' > util.list
find flexmark -name '*.java' > core.list
find flexmark-formatter -name '*.java' > fmt.list
find flexmark-ext-anchorlink flexmark-ext-tables -name '*.java' > ext.list
test "$(wc -l < util.list)" -eq 215
test "$(wc -l < core.list)" -eq 176
test "$(wc -l < fmt.list)" -eq 22
test "$(wc -l < ext.list)" -eq 30
test -f flexmark-util/com/vladsch/flexmark/util/ImageUtils.java

mkdir -p classes
javac --release 8 -encoding UTF-8 -Xlint:-options -d classes @util.list
javac --release 8 -encoding UTF-8 -Xlint:-options -cp classes -d classes @core.list
mkdir -p classes/com/vladsch/flexmark/internal/util
/bin/cp -a flexmark/com/vladsch/flexmark/internal/util/entities.properties classes/com/vladsch/flexmark/internal/util/
javac --release 8 -encoding UTF-8 -Xlint:-options -cp classes -d classes @fmt.list
javac --release 8 -encoding UTF-8 -Xlint:-options -cp classes -d classes @ext.list

cat > manifest.mf << 'EOF'
Manifest-Version: 1.0
Automatic-Module-Name: com.vladsch.flexmark

EOF
jar cfm flexmark-all.jar manifest.mf -C classes .
jar i flexmark-all.jar
javap -verbose -cp flexmark-all.jar com.vladsch.flexmark.parser.Parser | grep -F 'major version: 52'
jar --describe-module -f flexmark-all.jar > describe.txt
grep -F -q 'com.vladsch.flexmark automatic' describe.txt
if grep -F -q 'Unable' describe.txt; then
	cat describe.txt
	exit 1
fi

cat > flexmark-all.pom << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.vladsch.flexmark</groupId>
  <artifactId>flexmark-all</artifactId>
  <version>0.34.60</version>
  <name>flexmark-all</name>
  <description>flexmark core, util, formatter, tables, and anchorlink</description>
  <licenses>
    <license>
      <name>BSD-2-Clause</name>
    </license>
  </licenses>
</project>
EOF

%install
sysjar install --buildroot %{buildroot} \
	--artifact flexmark-all.pom:flexmark-all.jar \
	--file-name flexmark-all \
	--filelist .mfiles

%check
set -eo pipefail
mkdir -p check
cat > check/Smoke.java << 'EOF'
import com.vladsch.flexmark.ext.anchorlink.AnchorLinkExtension;
import com.vladsch.flexmark.ext.tables.TablesExtension;
import com.vladsch.flexmark.html.HtmlRenderer;
import com.vladsch.flexmark.parser.Parser;
import com.vladsch.flexmark.util.options.MutableDataSet;
import java.util.Arrays;

public class Smoke {
	public static void main(String[] args) {
		MutableDataSet options = new MutableDataSet();
		options.set(Parser.EXTENSIONS, Arrays.asList(TablesExtension.create(), AnchorLinkExtension.create()));
		Parser parser = Parser.builder(options).build();
		HtmlRenderer renderer = HtmlRenderer.builder(options).build();
		String html = renderer.render(parser.parse("# Gradle\n\n| A |\n| --- |\n| gradle |\n"));
		if (!html.contains("gradle") || !html.contains("<table") || !html.contains("id=\"gradle\"")) {
			throw new RuntimeException(html);
		}
		System.out.println("flexmark_ok table gradle");
	}
}
EOF
JAR=%{buildroot}%{_javadir}/flexmark-all.jar
test -f "$JAR"
javac --release 8 -encoding UTF-8 -Xlint:-options -cp "$JAR" -d check check/Smoke.java
java -cp "check:$JAR" Smoke > check/out.txt
cat check/out.txt
grep -F -q 'flexmark_ok table gradle' check/out.txt

%files -f .mfiles
%license LICENSE
