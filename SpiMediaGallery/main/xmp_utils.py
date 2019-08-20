from libxmp.utils import file_to_dict
import textwrap


class XmpUtils:
    @staticmethod
    def read_tags(file_path):
        tags = set()

        xmp = file_to_dict(file_path)

        if "http://www.digikam.org/ns/1.0/" in xmp:
            for tag_section in xmp['http://www.digikam.org/ns/1.0/']:
                if len(tag_section) == 0:
                    continue

                tag = tag_section[1]
                if tag != "":
                    tags.add(tag)

        return tags

    @staticmethod
    def generate_xmp(output_file, tags):
        # libxmp Python library seems to not be able to create a *new* XMP file, only
        # to open, read and modify files
        # xml Python library could do this but with some problems for the root node;
        # to have the finest control over the format the XML is hardcoded here
        with open(output_file, "w") as xmp_file:
            formatted_tags = ""
            for tag in tags:
                if formatted_tags != "":
                    formatted_tags += "\n"

                formatted_tags += "          <rdf:li>{}</rdf:li>".format(tag)

            xmp_file.write(textwrap.dedent("""\
                    <?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
                    <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 4.4.0-Exiv2">
                      <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
                        <rdf:Description rdf:about=""
                            xmlns:digiKam="http://www.digikam.org/ns/1.0/">
                          <digiKam:TagsList>
                            <rdf:Seq>
                    {}
                            </rdf:Seq>
                          </digiKam:TagsList>
                        </rdf:Description>
                      </rdf:RDF>
                    </x:xmpmeta>
                    <?xpacket end="w"?>
                  """).format(formatted_tags))
