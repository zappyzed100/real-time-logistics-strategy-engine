import L from "leaflet";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import type { MapCenterRow, MapOrderRow } from "../api/client.js";

type SimulationMapProps = {
    orderRows: MapOrderRow[];
    centerRows: MapCenterRow[];
    selectedOrderId?: string | null;
    selectedOrder?: MapOrderRow | null;
};

export const SimulationMap = memo(function SimulationMap({ orderRows, centerRows, selectedOrderId, selectedOrder }: SimulationMapProps) {
    const [zoomLevel, setZoomLevel] = useState<number>(5);
    const orderLayerRef = useRef<L.GeoJSON | null>(null);
    const orderFeatures = useMemo<GeoJSON.FeatureCollection<GeoJSON.Point>>(
        () => ({
            type: "FeatureCollection",
            features: orderRows.map((row) => ({
                type: "Feature",
                geometry: {
                    type: "Point",
                    coordinates: [row.customer_lon, row.customer_lat],
                },
                properties: {
                    ...row,
                },
            })),
        }),
        [orderRows],
    );

    const centerFeatures = useMemo<GeoJSON.FeatureCollection<GeoJSON.Point>>(
        () => ({
            type: "FeatureCollection",
            features: centerRows.map((row) => ({
                type: "Feature",
                geometry: {
                    type: "Point",
                    coordinates: [row.center_lon, row.center_lat],
                },
                properties: {
                    ...row,
                },
            })),
        }),
        [centerRows],
    );

    useEffect(() => {
        const orderLayer = orderLayerRef.current;
        if (!orderLayer) {
            return;
        }

        orderLayer.eachLayer((layer) => {
            if (!(layer instanceof L.CircleMarker)) {
                return;
            }

            const properties = layer.feature?.properties as MapOrderRow | undefined;
            if (!properties) {
                return;
            }

            const isSelected = properties.order_id === selectedOrderId;
            layer.setRadius(getOrderRadius(properties.weight_kg, zoomLevel, isSelected));
            layer.setStyle({
                fillColor: getOrderColor(properties),
                color: isSelected ? "#111827" : properties.is_unassigned ? "#7f1d1d" : "rgba(11, 26, 43, 0.12)",
                weight: isSelected ? 2.4 : properties.is_unassigned ? 1.6 : 0.9,
                opacity: 1,
                fillOpacity: isSelected ? 1 : properties.is_unassigned ? 0.98 : 0.72,
            });
        });
    }, [orderRows, selectedOrderId, zoomLevel]);

    return (
        <div className="map-panel">
            <MapContainer center={[36.2, 138.2]} zoom={5} scrollWheelZoom preferCanvas className="leaflet-map">
                <MapZoomTracker onZoomChange={setZoomLevel} />
                <SelectedOrderViewport selectedOrder={selectedOrder} />
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <GeoJSON
                    ref={(layer) => {
                        orderLayerRef.current = layer;
                    }}
                    data={orderFeatures}
                    pointToLayer={(feature, latlng) => {
                        const properties = feature.properties as MapOrderRow;
                        const isSelected = properties.order_id === selectedOrderId;

                        return L.circleMarker(latlng, {
                            radius: getOrderRadius(properties.weight_kg, zoomLevel, isSelected),
                            fillColor: getOrderColor(properties),
                            color: isSelected ? "#111827" : properties.is_unassigned ? "#7f1d1d" : "rgba(11, 26, 43, 0.12)",
                            weight: isSelected ? 2.4 : properties.is_unassigned ? 1.6 : 0.9,
                            opacity: 1,
                            fillOpacity: isSelected ? 1 : properties.is_unassigned ? 0.98 : 0.72,
                        });
                    }}
                    onEachFeature={(feature, layer) => {
                        const properties = feature.properties as MapOrderRow;
                        layer.bindPopup(
                            [
                                `<strong>注文ID:</strong> ${properties.order_id}`,
                                `<strong>配達拠点:</strong> ${getAssignedCenterDisplayText(properties)}`,
                                `<strong>重量:</strong> ${properties.weight_kg.toFixed(1)} kg`,
                                `<strong>配送コスト:</strong> ¥${Math.round(properties.simulated_cost).toLocaleString("ja-JP")}`,
                            ].join("<br>"),
                        );
                    }}
                />
                <GeoJSON
                    data={centerFeatures}
                    pointToLayer={(feature, latlng) => {
                        const properties = feature.properties as MapCenterRow;

                        return L.circleMarker(latlng, {
                            radius: Math.max(9, Math.min(19, 9 + properties.staffing_level * 0.12)),
                            fillColor: "rgba(18, 122, 142, 0.55)",
                            color: "rgba(7, 59, 76, 0.95)",
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.78,
                        });
                    }}
                    onEachFeature={(feature, layer) => {
                        const properties = feature.properties as MapCenterRow;
                        layer.bindPopup(
                            [
                                `<strong>拠点:</strong> ${properties.center_name}`,
                                `<strong>人員数:</strong> ${properties.staffing_level.toLocaleString("ja-JP")} 人`,
                                `<strong>固定費:</strong> ¥${Math.round(properties.fixed_cost).toLocaleString("ja-JP")}`,
                            ].join("<br>"),
                        );
                    }}
                />
            </MapContainer>
        </div>
    );
});

function MapZoomTracker({ onZoomChange }: { onZoomChange: (zoom: number) => void }) {
    useMapEvents({
        zoomend(event) {
            onZoomChange(event.target.getZoom());
        },
    });

    return null;
}

function SelectedOrderViewport({ selectedOrder }: { selectedOrder?: MapOrderRow | null }) {
    const map = useMap();

    useEffect(() => {
        if (!selectedOrder) {
            return;
        }

        map.flyTo([selectedOrder.customer_lat, selectedOrder.customer_lon], Math.max(map.getZoom(), 9), {
            animate: true,
            duration: 0.6,
        });
    }, [map, selectedOrder]);

    return null;
}

function getOrderRadius(weightKg: number, zoomLevel: number, isSelected: boolean): number {
    void weightKg;

    if (zoomLevel <= 5) {
        return isSelected ? 4.5 : 3;
    }

    return isSelected ? 6.5 : 5.5;
}

function getOrderColor(row: MapOrderRow): string {
    return `rgb(${row.color_r}, ${row.color_g}, ${row.color_b})`;
}

function getAssignedCenterDisplayText(row: MapOrderRow): string {
    if (row.assignment_status === "割当済" && row.assigned_center_name.trim() !== "") {
        return row.assigned_center_name;
    }

    return "未割当";
}