SCOPE = {
 "kitchener": {
  "council": ["Council Meeting", "Special Council Meeting"],
  "committee": ["Finance and Corporate Services Committee", "Planning and Strategic Initiatives Committee",
                "Community and Infrastructure Services Committee"],
  "check": ["Audit Committee", "Climate Change and Environment Committee", "Striking Committee"],
 },
 "region": {
  "council": ["Council Meeting", "Special Council", "Emergency Special Council", "Inaugural Council Meeting",
              "Board of Health (Regional Council)"],
  "committee": ["Administration and Finance", "Community and Health Services", "Planning and Works",
                "Planning and Works Regional Official Plan",
                "Planning and Works Statutory Public Meeting - Regional Official Plan Amendment", "Special Planning and Works",
                "Sustainability, Infrastructure, and Development", "Special Sustainability, Infrastructure, and Development",
                "Strategic Planning and Budget Committee", "Strategic Planning and Budget Public Input Committee",
                "Strategic Planning and Budget Sub-committee"],
  "check": ["Audit Committee", "All Councils", "Library Committee", "Licensing and Hearings", "Nominating Panel"],
 },
}
def body_of(c, name):
    for b, names in SCOPE[c].items():
        if name in names: return b
