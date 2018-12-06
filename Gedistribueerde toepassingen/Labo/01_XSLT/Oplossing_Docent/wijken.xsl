<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
    <xsl:output method="xml"/>

    <xsl:template match="/">
        <overzicht>
            <wijken>
                <xsl:variable name="wijken" select="root/element[not(wijkNr = preceding-sibling::element/wijkNr)]/wijkNr">
                </xsl:variable>
                <xsl:for-each select="$wijken">
                    <xsl:sort select="." data-type="number"></xsl:sort>
                    <wijk>
                        <xsl:attribute name="nr">                    
                            <xsl:value-of select="."/> 
                        </xsl:attribute>
                        <naam>
                            <xsl:value-of select="../wijknaam"/> 
                        </naam>
                    </wijk>
                </xsl:for-each>
            </wijken>
        </overzicht>
    </xsl:template>
</xsl:stylesheet>
