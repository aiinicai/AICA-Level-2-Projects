from django.db import models
from simple_history.models import HistoricalRecords


class Entity(models.Model):
    """
    Legal entity — the parent listed company, or a subsidiary. Exists so
    multi-entity consolidation (blueprint §05, §08) can roll standalone
    PP&E registers up into a consolidated Ind AS note later without a
    schema change.
    """

    name = models.CharField(max_length=255, unique=True)
    cin = models.CharField("Corporate Identity Number (CIN)", max_length=32, blank=True)
    is_listed_parent = models.BooleanField(default=False)
    registered_office = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Entities"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Location(models.Model):
    """
    Site -> Building -> Floor -> Room/Zone hierarchy (blueprint §02).
    Self-referencing tree rather than four separate tables, so a company can
    add or drop levels to match how its plants/offices are actually
    organised, per the blueprint's explicit instruction.
    """

    class NodeType(models.TextChoices):
        SITE = "SITE", "Site"
        BUILDING = "BUILDING", "Building"
        FLOOR = "FLOOR", "Floor"
        ROOM = "ROOM", "Room / Zone"

    entity = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="locations")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    node_type = models.CharField(max_length=16, choices=NodeType.choices)
    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=32, help_text="Short code used in the location breadcrumb, e.g. B2-F3-R01.")
    address = models.TextField(blank=True)
    floor_plan_image = models.ImageField(
        upload_to="floor_plans/", blank=True, null=True,
        help_text="Optional floor-plan image for the site/floor-plan overlay view.",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["entity", "node_type", "name"]
        unique_together = [("parent", "code")]

    def __str__(self):
        return self.breadcrumb()

    def breadcrumb(self):
        parts = [self.name]
        node = self.parent
        while node is not None:
            parts.append(node.name)
            node = node.parent
        return " / ".join(reversed(parts))

    def full_path_codes(self):
        parts = [self.code]
        node = self.parent
        while node is not None:
            parts.append(node.code)
            node = node.parent
        return "-".join(reversed(parts))

    def descendant_ids(self):
        """All node IDs in this subtree, including self — used for rollups."""
        ids = [self.id]
        for child in self.children.all():
            ids.extend(child.descendant_ids())
        return ids
